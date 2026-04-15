from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence

from .config import runtime_sku, settings
from .part_catalog import sort_in_catalog_order
from .store import (
    ActionResult,
    InventoryStore,
    Kit,
    KitComponent,
    NotFoundError,
    Part,
    Transaction,
    ValidationError,
)


class MockStore(InventoryStore):
    def __init__(self, db_path: Path, seed_file: Path, allow_negative_stock: bool = False):
        self.db_path = Path(db_path)
        self.seed_file = Path(seed_file)
        self.allow_negative_stock = allow_negative_stock
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()
        self._seed_if_empty()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS parts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sku TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    container_label TEXT NOT NULL,
                    starting_qty INTEGER NOT NULL DEFAULT 0,
                    reorder_level INTEGER NOT NULL DEFAULT 0,
                    parts_per_po_unit INTEGER NOT NULL DEFAULT 1,
                    parts_per_rad_unit INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS kits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS kit_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kit_id INTEGER NOT NULL,
                    part_sku TEXT NOT NULL,
                    qty_per_kit INTEGER NOT NULL,
                    FOREIGN KEY (kit_id) REFERENCES kits(id),
                    FOREIGN KEY (part_sku) REFERENCES parts(sku)
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    sku TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    delta INTEGER NOT NULL,
                    batch_id TEXT,
                    operator TEXT,
                    note TEXT,
                    source TEXT,
                    FOREIGN KEY (sku) REFERENCES parts(sku)
                );
                """
            )
            self._ensure_column('parts', 'parts_per_po_unit', 'INTEGER NOT NULL DEFAULT 1')
            self._ensure_column('parts', 'parts_per_rad_unit', 'INTEGER NOT NULL DEFAULT 0')

    def _ensure_column(self, table: str, column: str, sql_type: str) -> None:
        with self._connect() as conn:
            columns = {row['name'] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if column not in columns:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")

    def _seed_if_empty(self) -> None:
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS c FROM parts").fetchone()["c"]
            if count:
                return
            seed = json.loads(self.seed_file.read_text())
            conn.executemany(
                "INSERT INTO parts (sku, name, container_label, starting_qty, reorder_level, parts_per_po_unit, parts_per_rad_unit) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        part["sku"],
                        part["name"],
                        part.get("container_label", part["sku"]),
                        int(part.get("starting_qty", 0)),
                        int(part.get("reorder_level", 0)),
                        int(part.get("parts_per_po_unit", 1) or 1),
                        int(part.get("parts_per_rad_unit", 0) or 0),
                    )
                    for part in seed.get("parts", [])
                ],
            )
            for kit in seed.get("kits", []):
                cur = conn.execute("INSERT INTO kits (code, name) VALUES (?, ?)", (kit["code"], kit["name"]))
                kit_id = cur.lastrowid
                conn.executemany(
                    "INSERT INTO kit_items (kit_id, part_sku, qty_per_kit) VALUES (?, ?, ?)",
                    [
                        (kit_id, comp["sku"], int(comp["qty_per_kit"]))
                        for comp in kit.get("components", [])
                    ],
                )

    def reset_from_seed(self) -> None:
        if self.db_path.exists():
            self.db_path.unlink()
        self._ensure_schema()
        self._seed_if_empty()

    def _now(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    def _part_row_to_model(self, row: sqlite3.Row) -> Part:
        return Part(
            sku=row["sku"],
            name=row["name"],
            container_label=row["container_label"],
            starting_qty=int(row["starting_qty"] or 0),
            on_hand=int(row["on_hand"] or 0),
            reorder_level=int(row["reorder_level"] or 0),
            external_id=str(row["id"]),
            parts_per_po_unit=int(row["parts_per_po_unit"] or 1) if "parts_per_po_unit" in row.keys() else 1,
            parts_per_rad_unit=int(row["parts_per_rad_unit"] or 0) if "parts_per_rad_unit" in row.keys() else 0,
        )

    def _part_query(self) -> str:
        return (
            "SELECT p.id, p.sku, p.name, p.container_label, p.starting_qty, p.reorder_level, p.parts_per_po_unit, p.parts_per_rad_unit, "
            "COALESCE(p.starting_qty + SUM(t.delta), p.starting_qty) AS on_hand "
            "FROM parts p "
            "LEFT JOIN transactions t ON t.sku = p.sku "
        )

    def list_parts(self) -> Sequence[Part]:
        with self._connect() as conn:
            rows = conn.execute(
                self._part_query()
                + "GROUP BY p.id, p.sku, p.name, p.container_label, p.starting_qty, p.reorder_level, p.parts_per_po_unit, p.parts_per_rad_unit "
            ).fetchall()
        parts = [self._part_row_to_model(row) for row in rows]
        return sort_in_catalog_order(parts, get_sku=lambda part: part.sku, get_name=lambda part: part.name)

    def get_part(self, sku: str) -> Part:
        with self._connect() as conn:
            row = conn.execute(
                self._part_query()
                + "WHERE p.sku = ? "
                + "GROUP BY p.id, p.sku, p.name, p.container_label, p.starting_qty, p.reorder_level, p.parts_per_po_unit, p.parts_per_rad_unit",
                (sku,),
            ).fetchone()
        if not row:
            raise NotFoundError(f"Part '{sku}' was not found.")
        return self._part_row_to_model(row)

    def list_transactions(self, limit: int = 50) -> Sequence[Transaction]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT t.created_at, t.sku, p.name AS part_name, t.action, t.quantity, t.delta,
                       t.batch_id, t.operator, t.note, t.source
                FROM transactions t
                JOIN parts p ON p.sku = t.sku
                ORDER BY t.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            Transaction(
                created_at=row["created_at"],
                sku=row["sku"],
                part_name=row["part_name"],
                action=row["action"],
                quantity=int(row["quantity"]),
                delta=int(row["delta"]),
                batch_id=row["batch_id"],
                operator=row["operator"],
                note=row["note"],
                source=row["source"],
            )
            for row in rows
        ]

    def list_kits(self) -> Sequence[Kit]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, code, name FROM kits ORDER BY name").fetchall()
        return [Kit(code=row["code"], name=row["name"], external_id=str(row["id"])) for row in rows]

    def get_kit(self, code: str) -> Kit:
        with self._connect() as conn:
            kit_row = conn.execute("SELECT id, code, name FROM kits WHERE code = ?", (code,)).fetchone()
            if not kit_row:
                raise NotFoundError(f"Kit '{code}' was not found.")
            comp_rows = conn.execute(
                """
                SELECT p.id, p.sku, p.name, p.container_label, p.starting_qty, p.reorder_level,
                       ki.qty_per_kit,
                       COALESCE(p.starting_qty + SUM(t.delta), p.starting_qty) AS on_hand
                FROM parts p
                JOIN kit_items ki ON ki.part_sku = p.sku
                LEFT JOIN transactions t ON t.sku = p.sku
                WHERE ki.kit_id = ?
                GROUP BY p.id, p.sku, p.name, p.container_label, p.starting_qty, p.reorder_level, p.parts_per_po_unit, p.parts_per_rad_unit, ki.qty_per_kit
                ORDER BY p.name
                """,
                (kit_row["id"],),
            ).fetchall()
        components = [
            KitComponent(
                sku=row["sku"],
                part_name=row["name"],
                qty_per_kit=int(row["qty_per_kit"]),
                on_hand=int(row["on_hand"]),
            )
            for row in comp_rows
        ]
        return Kit(code=kit_row["code"], name=kit_row["name"], external_id=str(kit_row["id"]), components=components)

    def get_whole_unit(self) -> Kit | None:
        parts = self.list_parts()
        components = [
            KitComponent(
                sku=part.sku,
                part_name=part.name,
                qty_per_kit=int(part.parts_per_rad_unit or 0),
                on_hand=part.on_hand,
            )
            for part in parts
            if int(getattr(part, "parts_per_rad_unit", 0) or 0) > 0
        ]
        if not components:
            return None
        return Kit(code='WHOLE-RAD-BOX', name='Whole RAD Box Unit', components=components)

    def _validate_action(self, action: str) -> None:
        if action not in {"add", "subtract"}:
            raise ValidationError("Action must be 'add' or 'subtract'.")

    def _validate_quantity(self, quantity: int) -> None:
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1.")

    def apply_part_action(
        self,
        sku: str,
        action: str,
        quantity: int,
        operator: str = "",
        note: str = "",
        source: str = "",
    ) -> ActionResult:
        self._validate_action(action)
        self._validate_quantity(quantity)
        part = self.get_part(sku)
        delta = quantity if action == "add" else -quantity
        if not self.allow_negative_stock and part.on_hand + delta < 0:
            raise ValidationError(
                f"Cannot subtract {quantity} from {part.name}. Only {part.on_hand} currently on hand."
            )

        batch_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO transactions (created_at, sku, action, quantity, delta, batch_id, operator, note, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (self._now(), sku, action, quantity, delta, batch_id, operator.strip(), note.strip(), source.strip()),
            )
        updated = self.get_part(sku)
        return ActionResult(
            ok=True,
            message=f"{action.title()}ed {quantity} x {updated.name}. New on-hand quantity: {updated.on_hand}.",
            batch_id=batch_id,
            touched_parts=[updated],
            transactions_created=1,
        )

    def apply_kit_action(
        self,
        code: str,
        action: str,
        operator: str = "",
        note: str = "",
        source: str = "",
    ) -> ActionResult:
        self._validate_action(action)
        kit = self.get_kit(code)
        if not kit.components:
            raise ValidationError(f"Kit '{kit.name}' has no components.")

        multiplier = 1 if action == "add" else -1
        if not self.allow_negative_stock and action == "subtract":
            shortages = [
                comp for comp in kit.components if comp.on_hand - comp.qty_per_kit < 0
            ]
            if shortages:
                details = "; ".join(
                    f"{comp.part_name}: need {comp.qty_per_kit}, have {comp.on_hand}" for comp in shortages
                )
                raise ValidationError(f"Kit subtract blocked because stock would go negative. {details}")

        batch_id = str(uuid.uuid4())
        with self._connect() as conn:
            now = self._now()
            for comp in kit.components:
                conn.execute(
                    """
                    INSERT INTO transactions (created_at, sku, action, quantity, delta, batch_id, operator, note, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        now,
                        comp.sku,
                        f"kit_{action}",
                        comp.qty_per_kit,
                        multiplier * comp.qty_per_kit,
                        batch_id,
                        operator.strip(),
                        note.strip(),
                        source.strip() or f"qr:kit:{code}:{action}",
                    ),
                )
        touched_parts = [self.get_part(comp.sku) for comp in kit.components]
        return ActionResult(
            ok=True,
            message=f"Applied {action} for kit {kit.name}. Updated {len(touched_parts)} parts.",
            batch_id=batch_id,
            touched_parts=touched_parts,
            transactions_created=len(touched_parts),
        )

    def apply_whole_unit_action(
        self,
        action: str,
        operator: str = "",
        note: str = "",
        source: str = "",
    ) -> ActionResult:
        self._validate_action(action)
        whole = self.get_whole_unit()
        if not whole or not whole.components:
            raise ValidationError("Whole RAD Box Unit is not configured. Add values to Parts per RAD Unit first.")

        multiplier = 1 if action == "add" else -1
        if not self.allow_negative_stock and action == "subtract":
            shortages = [comp for comp in whole.components if comp.on_hand - comp.qty_per_kit < 0]
            if shortages:
                details = "; ".join(f"{comp.part_name}: need {comp.qty_per_kit}, have {comp.on_hand}" for comp in shortages)
                raise ValidationError(f"Whole RAD Box subtract blocked because stock would go negative. {details}")

        batch_id = str(uuid.uuid4())
        now = self._now()
        with self._connect() as conn:
            for comp in whole.components:
                conn.execute(
                    """
                    INSERT INTO transactions (created_at, sku, action, quantity, delta, batch_id, operator, note, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        now,
                        comp.sku,
                        action,
                        comp.qty_per_kit,
                        multiplier * comp.qty_per_kit,
                        batch_id,
                        operator.strip(),
                        note.strip(),
                        source.strip() or f"qr:whole_unit:{action}",
                    ),
                )
        touched_parts = [self.get_part(comp.sku) for comp in whole.components]
        return ActionResult(
            ok=True,
            message=f"Applied {action} for {whole.name}. Updated {len(touched_parts)} parts.",
            batch_id=batch_id,
            touched_parts=touched_parts,
            transactions_created=len(touched_parts),
        )


def build_mock_store() -> MockStore:
    return MockStore(
        db_path=settings.mock_db_path,
        seed_file=settings.seed_file,
        allow_negative_stock=settings.allow_negative_stock,
    )
