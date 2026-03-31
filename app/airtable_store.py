from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence

import requests

from .config import settings
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


class AirtableStore(InventoryStore):
    def __init__(self, pat: str, base_id: str, allow_negative_stock: bool = False):
        if not pat or not base_id:
            raise ValidationError("AIRTABLE_PAT and AIRTABLE_BASE_ID are required for STORE_MODE=airtable.")
        self.pat = pat
        self.base_id = base_id
        self.allow_negative_stock = allow_negative_stock
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.pat}",
                "Content-Type": "application/json",
            }
        )
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"

    def _request(self, method: str, table: str, *, params: dict[str, Any] | None = None, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}/{requests.utils.quote(table, safe='')}"
        response = self.session.request(method, url, params=params, json=json_body, timeout=30)
        if response.status_code >= 400:
            try:
                payload = response.json()
            except Exception:
                payload = {"error": {"message": response.text}}
            message = payload.get("error", {}).get("message", response.text)
            raise ValidationError(f"Airtable API error on {table}: {message}")
        return response.json() if response.text else {}

    def _list_all_records(self, table: str, fields: list[str] | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"pageSize": 100}
        if fields:
            params["fields[]"] = fields
        records: list[dict[str, Any]] = []
        offset: str | None = None
        while True:
            if offset:
                params["offset"] = offset
            payload = self._request("GET", table, params=params)
            records.extend(payload.get("records", []))
            offset = payload.get("offset")
            if not offset:
                break
        return records

    def _create_records(self, table: str, records: list[dict[str, Any]]) -> None:
        for i in range(0, len(records), 10):
            chunk = records[i : i + 10]
            self._request("POST", table, json_body={"records": chunk, "typecast": True})

    def _now(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    def _coerce_int(self, value: Any) -> int:
        if value is None or value == "":
            return 0
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(math.floor(value)) if isinstance(value, float) else int(value)
        return int(str(value))

    def _load_parts(self) -> tuple[list[Part], dict[str, str], dict[str, Part]]:
        raw_parts = self._list_all_records(
            settings.airtable_parts_table,
            fields=[
                settings.field_part_sku,
                settings.field_part_name,
                settings.field_part_container,
                settings.field_part_starting_qty,
                settings.field_part_on_hand,
                settings.field_part_reorder_level,
            ],
        )
        parts: list[Part] = []
        sku_to_id: dict[str, str] = {}
        sku_to_part: dict[str, Part] = {}
        for record in raw_parts:
            fields = record.get("fields", {})
            sku = str(fields.get(settings.field_part_sku, "")).strip()
            if not sku:
                continue
            part = Part(
                sku=sku,
                name=str(fields.get(settings.field_part_name, sku)),
                container_label=str(fields.get(settings.field_part_container, sku)),
                starting_qty=self._coerce_int(fields.get(settings.field_part_starting_qty, 0)),
                on_hand=self._coerce_int(fields.get(settings.field_part_on_hand, fields.get(settings.field_part_starting_qty, 0))),
                reorder_level=self._coerce_int(fields.get(settings.field_part_reorder_level, 0)),
                external_id=record["id"],
            )
            parts.append(part)
            sku_to_id[sku] = record["id"]
            sku_to_part[sku] = part
        parts.sort(key=lambda p: p.name.lower())
        return parts, sku_to_id, sku_to_part

    def list_parts(self) -> Sequence[Part]:
        parts, _, _ = self._load_parts()
        return parts

    def get_part(self, sku: str) -> Part:
        _, _, sku_to_part = self._load_parts()
        if sku not in sku_to_part:
            raise NotFoundError(f"Part '{sku}' was not found in Airtable.")
        return sku_to_part[sku]

    def list_transactions(self, limit: int = 50) -> Sequence[Transaction]:
        _, _, sku_to_part = self._load_parts()
        raw_txns = self._list_all_records(
            settings.airtable_transactions_table,
            fields=[
                settings.field_txn_sku,
                settings.field_txn_action,
                settings.field_txn_quantity,
                settings.field_txn_delta,
                settings.field_txn_batch_id,
                settings.field_txn_operator,
                settings.field_txn_note,
                settings.field_txn_source,
                settings.field_txn_scanned_at,
            ],
        )
        txns: list[Transaction] = []
        for record in raw_txns:
            fields = record.get("fields", {})
            sku = str(fields.get(settings.field_txn_sku, "")).strip()
            part_name = sku_to_part.get(sku).name if sku in sku_to_part else sku
            txns.append(
                Transaction(
                    created_at=str(fields.get(settings.field_txn_scanned_at, record.get("createdTime", ""))),
                    sku=sku,
                    part_name=part_name,
                    action=str(fields.get(settings.field_txn_action, "")),
                    quantity=self._coerce_int(fields.get(settings.field_txn_quantity, 0)),
                    delta=self._coerce_int(fields.get(settings.field_txn_delta, 0)),
                    batch_id=str(fields.get(settings.field_txn_batch_id, "") or "") or None,
                    operator=str(fields.get(settings.field_txn_operator, "") or "") or None,
                    note=str(fields.get(settings.field_txn_note, "") or "") or None,
                    source=str(fields.get(settings.field_txn_source, "") or "") or None,
                )
            )
        txns.sort(key=lambda t: t.created_at, reverse=True)
        return txns[:limit]

    def _load_kits(self) -> tuple[dict[str, Kit], dict[str, list[KitComponent]]]:
        parts, id_by_sku, sku_to_part = self._load_parts()
        part_by_record_id = {part.external_id: part for part in parts if part.external_id}

        raw_kits = self._list_all_records(
            settings.airtable_kits_table,
            fields=[settings.field_kit_code, settings.field_kit_name],
        )
        record_id_to_kit_code: dict[str, str] = {}
        kits_by_code: dict[str, Kit] = {}
        for record in raw_kits:
            fields = record.get("fields", {})
            code = str(fields.get(settings.field_kit_code, "")).strip()
            if not code:
                continue
            kit = Kit(
                code=code,
                name=str(fields.get(settings.field_kit_name, code)),
                external_id=record["id"],
                components=[],
            )
            kits_by_code[code] = kit
            record_id_to_kit_code[record["id"]] = code

        raw_kit_items = self._list_all_records(
            settings.airtable_kit_items_table,
            fields=[settings.field_kit_item_kit, settings.field_kit_item_part, settings.field_kit_item_qty],
        )
        comps_by_code: dict[str, list[KitComponent]] = {code: [] for code in kits_by_code}
        for record in raw_kit_items:
            fields = record.get("fields", {})
            kit_ids = fields.get(settings.field_kit_item_kit) or []
            part_ids = fields.get(settings.field_kit_item_part) or []
            if not kit_ids or not part_ids:
                continue
            kit_code = record_id_to_kit_code.get(kit_ids[0])
            part = part_by_record_id.get(part_ids[0])
            if not kit_code or not part:
                continue
            comps_by_code.setdefault(kit_code, []).append(
                KitComponent(
                    sku=part.sku,
                    part_name=part.name,
                    qty_per_kit=self._coerce_int(fields.get(settings.field_kit_item_qty, 1)),
                    on_hand=part.on_hand,
                )
            )
        for code, comps in comps_by_code.items():
            comps.sort(key=lambda c: c.part_name.lower())
            if code in kits_by_code:
                kits_by_code[code].components = comps
        return kits_by_code, comps_by_code

    def list_kits(self) -> Sequence[Kit]:
        kits_by_code, _ = self._load_kits()
        return sorted(kits_by_code.values(), key=lambda k: k.name.lower())

    def get_kit(self, code: str) -> Kit:
        kits_by_code, _ = self._load_kits()
        if code not in kits_by_code:
            raise NotFoundError(f"Kit '{code}' was not found in Airtable.")
        return kits_by_code[code]

    def _validate_action(self, action: str) -> None:
        if action not in {"add", "subtract"}:
            raise ValidationError("Action must be 'add' or 'subtract'.")

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
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1.")
        _, sku_to_id, sku_to_part = self._load_parts()
        if sku not in sku_to_id:
            raise NotFoundError(f"Part '{sku}' was not found in Airtable.")
        part = sku_to_part[sku]
        delta = quantity if action == "add" else -quantity
        if not self.allow_negative_stock and part.on_hand + delta < 0:
            raise ValidationError(
                f"Cannot subtract {quantity} from {part.name}. Only {part.on_hand} currently on hand."
            )

        batch_id = str(uuid.uuid4())
        fields: Dict[str, Any] = {
            settings.field_txn_part: [sku_to_id[sku]],
            settings.field_txn_sku: sku,
            settings.field_txn_action: action,
            settings.field_txn_quantity: quantity,
            settings.field_txn_delta: delta,
            settings.field_txn_batch_id: batch_id,
            settings.field_txn_operator: operator.strip(),
            settings.field_txn_note: note.strip(),
            settings.field_txn_source: source.strip() or f"qr:part:{sku}:{action}",
            settings.field_txn_scanned_at: self._now(),
        }
        self._create_records(settings.airtable_transactions_table, [{"fields": fields}])
        updated = self.get_part(sku)
        return ActionResult(
            ok=True,
            message=f"Logged {action} of {quantity} x {updated.name}. Airtable will update on-hand via rollups/formulas.",
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
        _, sku_to_id, sku_to_part = self._load_parts()
        kit = self.get_kit(code)
        if not kit.components:
            raise ValidationError(f"Kit '{kit.name}' has no components.")
        if not self.allow_negative_stock and action == "subtract":
            shortages = [comp for comp in kit.components if comp.on_hand - comp.qty_per_kit < 0]
            if shortages:
                details = "; ".join(
                    f"{comp.part_name}: need {comp.qty_per_kit}, have {comp.on_hand}" for comp in shortages
                )
                raise ValidationError(f"Kit subtract blocked because stock would go negative. {details}")

        multiplier = 1 if action == "add" else -1
        batch_id = str(uuid.uuid4())
        scanned_at = self._now()
        records: List[dict[str, Any]] = []
        for comp in kit.components:
            if comp.sku not in sku_to_id:
                raise ValidationError(f"Part '{comp.sku}' is missing from the Airtable parts table.")
            records.append(
                {
                    "fields": {
                        settings.field_txn_part: [sku_to_id[comp.sku]],
                        settings.field_txn_sku: comp.sku,
                        settings.field_txn_action: f"kit_{action}",
                        settings.field_txn_quantity: comp.qty_per_kit,
                        settings.field_txn_delta: multiplier * comp.qty_per_kit,
                        settings.field_txn_batch_id: batch_id,
                        settings.field_txn_operator: operator.strip(),
                        settings.field_txn_note: note.strip(),
                        settings.field_txn_source: source.strip() or f"qr:kit:{code}:{action}",
                        settings.field_txn_scanned_at: scanned_at,
                    }
                }
            )
        self._create_records(settings.airtable_transactions_table, records)
        touched_parts = [sku_to_part[comp.sku] for comp in kit.components if comp.sku in sku_to_part]
        return ActionResult(
            ok=True,
            message=f"Logged {action} for kit {kit.name}. Airtable will update each linked part's on-hand value.",
            batch_id=batch_id,
            touched_parts=touched_parts,
            transactions_created=len(records),
        )


def build_airtable_store() -> AirtableStore:
    return AirtableStore(
        pat=settings.airtable_pat,
        base_id=settings.airtable_base_id,
        allow_negative_stock=settings.allow_negative_stock,
    )
