from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Sequence

import requests

from .config import settings
from .part_catalog import find_catalog_entry, sort_in_catalog_order
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
            raise ValidationError('AIRTABLE_PAT and AIRTABLE_BASE_ID are required for STORE_MODE=airtable.')
        self.pat = pat
        self.base_id = base_id
        self.allow_negative_stock = allow_negative_stock
        self.session = requests.Session()
        self.session.headers.update(
            {
                'Authorization': f'Bearer {self.pat}',
                'Content-Type': 'application/json',
            }
        )
        self.base_url = f'https://api.airtable.com/v0/{self.base_id}'
        self._resolved_parts_table: str | None = None

    def _request(
        self,
        method: str,
        table: str,
        *,
        record_id: str | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{requests.utils.quote(table, safe='')}"
        if record_id:
            url += f"/{requests.utils.quote(record_id, safe='')}"
        try:
            response = self.session.request(method, url, params=params, json=json_body, timeout=30)
        except requests.RequestException as exc:
            raise ValidationError(f'Airtable API request failed on {table}: {exc}') from exc
        if response.status_code >= 400:
            try:
                payload = response.json()
            except Exception:
                payload = {'error': {'message': response.text}}
            message = payload.get('error', {}).get('message', response.text)
            raise ValidationError(f'Airtable API error on {table}: {message}')
        return response.json() if response.text else {}

    def _list_all_records(self, table: str, fields: list[str] | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {'pageSize': 100}
        fields = [field for field in (fields or []) if field]
        if fields:
            params['fields[]'] = fields
        records: list[dict[str, Any]] = []
        offset: str | None = None
        while True:
            if offset:
                params['offset'] = offset
            payload = self._request('GET', table, params=params)
            records.extend(payload.get('records', []))
            offset = payload.get('offset')
            if not offset:
                break
        return records

    def _create_records(self, table: str, records: list[dict[str, Any]]) -> None:
        for i in range(0, len(records), 10):
            chunk = records[i : i + 10]
            self._request('POST', table, json_body={'records': chunk, 'typecast': True})

    def _update_record(self, table: str, record_id: str, fields: dict[str, Any]) -> None:
        self._request('PATCH', table, record_id=record_id, json_body={'fields': fields, 'typecast': True})

    def _now(self) -> str:
        mst = timezone(timedelta(hours=-7), name='MST')
        return datetime.now(timezone.utc).astimezone(mst).replace(microsecond=0).strftime('%Y-%m-%d %I:%M:%S %p MST')

    def _coerce_int(self, value: Any) -> int:
        if value is None or value == '':
            return 0
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(math.floor(value)) if isinstance(value, float) else int(value)
        text = str(value).strip().replace('$', '').replace(',', '')
        if text == '':
            return 0
        return int(float(text))

    def _build_part(self, record: dict[str, Any]) -> Part | None:
        fields = record.get('fields', {})
        raw_name = str(fields.get(settings.field_part_name, '')).strip() if settings.field_part_name else ''
        configured_sku = str(fields.get(settings.field_part_sku, '')).strip() if settings.field_part_sku else ''
        catalog_entry = find_catalog_entry(raw_name) if settings.airtable_filter_to_catalog else None
        if settings.airtable_filter_to_catalog and not catalog_entry:
            return None

        sku = catalog_entry.sku if catalog_entry else (configured_sku or raw_name or record['id'])
        name = raw_name or (catalog_entry.display_name if catalog_entry else (configured_sku or record['id']))

        if settings.field_part_container:
            container_label = str(fields.get(settings.field_part_container, '')).strip()
        else:
            container_label = ''

        starting_qty = self._coerce_int(fields.get(settings.field_part_starting_qty, 0)) if settings.field_part_starting_qty else 0
        if settings.field_part_on_hand:
            on_hand = self._coerce_int(fields.get(settings.field_part_on_hand, starting_qty))
        else:
            on_hand = starting_qty
        reorder_level = self._coerce_int(fields.get(settings.field_part_reorder_level, 0)) if settings.field_part_reorder_level else 0

        parts_per_po_unit = self._coerce_int(fields.get(settings.field_part_parts_per_po_unit, 1)) if settings.field_part_parts_per_po_unit else 1
        if parts_per_po_unit <= 0:
            parts_per_po_unit = 1

        return Part(
            sku=sku,
            name=name,
            container_label=container_label,
            starting_qty=starting_qty,
            on_hand=on_hand,
            reorder_level=reorder_level,
            external_id=record['id'],
            parts_per_po_unit=parts_per_po_unit,
        )

    def _candidate_parts_tables(self) -> list[str]:
        candidates: list[str] = []
        for table in [settings.airtable_parts_table, 'Inventory', 'BOM Line Items']:
            table = (table or '').strip()
            if table and table not in candidates:
                candidates.append(table)
        return candidates

    def _load_parts(self) -> tuple[list[Part], dict[str, str], dict[str, Part]]:
        raw_parts: list[dict[str, Any]] | None = None
        last_error: ValidationError | None = None
        selected_table: str | None = None
        fields = [
            settings.field_part_sku,
            settings.field_part_name,
            settings.field_part_container,
            settings.field_part_starting_qty,
            settings.field_part_on_hand,
            settings.field_part_reorder_level,
            settings.field_part_parts_per_po_unit,
        ]
        for table in self._candidate_parts_tables():
            try:
                raw_parts = self._list_all_records(table, fields=fields)
                selected_table = table
                break
            except ValidationError as exc:
                last_error = exc
                if self._is_missing_table_error(exc, table):
                    continue
                raise
        if raw_parts is None or selected_table is None:
            if last_error is not None:
                raise last_error
            raise ValidationError('Could not load the Airtable inventory table.')

        self._resolved_parts_table = selected_table
        parts: list[Part] = []
        sku_to_id: dict[str, str] = {}
        sku_to_part: dict[str, Part] = {}
        for record in raw_parts:
            part = self._build_part(record)
            if not part:
                continue
            parts.append(part)
            sku_to_id[part.sku] = record['id']
            sku_to_part[part.sku] = part
        return parts, sku_to_id, sku_to_part

    def list_parts(self) -> Sequence[Part]:
        parts, _, _ = self._load_parts()
        return sort_in_catalog_order(parts, get_sku=lambda part: part.sku, get_name=lambda part: part.name)

    def get_part(self, sku: str) -> Part:
        _, _, sku_to_part = self._load_parts()
        if sku not in sku_to_part:
            raise NotFoundError(f"Part '{sku}' was not found in Airtable.")
        return sku_to_part[sku]

    def list_purchase_orders(self) -> list[dict[str, str]]:
        table = 'Purchase Orders'
        try:
            raw_pos = self._list_all_records(table, fields=['PO Number', 'Order Date', 'Status'])
        except ValidationError as exc:
            if self._is_missing_table_error(exc, table):
                return []
            raise

        purchase_orders: list[dict[str, str]] = []
        for record in raw_pos:
            fields = record.get('fields', {})
            po_number = self._first_field_value(fields, 'PO Number', default='')
            order_date = self._first_field_value(fields, 'Order Date', default='')
            status = self._first_field_value(fields, 'Status', default='')
            purchase_orders.append(
                {
                    'id': record['id'],
                    'po_number': str(po_number or ''),
                    'order_date': str(order_date or ''),
                    'status': str(status or ''),
                }
            )
        return purchase_orders

    def _is_missing_table_error(self, exc: Exception, table: str) -> bool:
        text = str(exc).lower()
        return table.lower() in text and ('table' in text and ('not found' in text or 'could not find' in text or 'unknown field name' in text))

    def _transactions_table_configured(self) -> bool:
        return bool((settings.airtable_transactions_table or '').strip())

    def _first_field_value(self, fields: dict[str, Any], *names: str, default: Any = '') -> Any:
        for name in names:
            if not name:
                continue
            if name in fields:
                return fields.get(name)
        return default

    def _linked_record_ids(self, fields: dict[str, Any], *names: str) -> list[str]:
        value = self._first_field_value(fields, *names, default=[])
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        text = str(value).strip()
        return [text] if text else []

    def _transaction_type_label(self, action: str, purchase_order_record_id: str | None = None) -> str:
        normalized = (action or '').strip().lower()
        if normalized == 'undo_receive':
            return 'Undo Receive'
        if normalized == 'receive':
            return 'Receive'
        if normalized == 'subtract':
            return 'Subtract'
        return 'Add'

    def _transaction_sort_value(self, value: str) -> datetime:
        text = (value or '').strip()
        if not text:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            return datetime.strptime(text, '%Y-%m-%d %I:%M:%S %p MST').replace(tzinfo=timezone(timedelta(hours=-7), name='MST'))
        except ValueError:
            pass
        try:
            return datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

    def list_transactions(self, limit: int = 50) -> Sequence[Transaction]:
        if not self._transactions_table_configured():
            return []
        parts, _, _ = self._load_parts()
        part_by_record_id = {part.external_id: part for part in parts if part.external_id}
        try:
            raw_txns = self._list_all_records(settings.airtable_transactions_table)
        except ValidationError as exc:
            if self._is_missing_table_error(exc, settings.airtable_transactions_table):
                return []
            raise

        txns: list[Transaction] = []
        for record in raw_txns:
            fields = record.get('fields', {})
            linked_part_ids = self._linked_record_ids(fields, 'Part', settings.field_txn_part)
            linked_part = part_by_record_id.get(linked_part_ids[0]) if linked_part_ids else None
            delta = self._coerce_int(
                self._first_field_value(fields, 'Quantity Change', settings.field_txn_delta, 'Delta', default=0)
            )
            quantity_value = self._first_field_value(fields, settings.field_txn_quantity, 'Quantity', default=None)
            quantity = self._coerce_int(quantity_value) if quantity_value not in (None, '') else abs(delta)
            sku = linked_part.sku if linked_part else str(
                self._first_field_value(fields, settings.field_txn_sku, 'SKU', default='')
            ).strip()
            part_name = linked_part.name if linked_part else sku
            txns.append(
                Transaction(
                    created_at=str(
                        self._first_field_value(fields, 'Timestamp', settings.field_txn_scanned_at, 'Scanned At', default=record.get('createdTime', ''))
                    ),
                    sku=sku,
                    part_name=part_name,
                    action=str(
                        self._first_field_value(fields, 'Transaction Type', settings.field_txn_action, 'Action', default='')
                    ),
                    quantity=quantity,
                    delta=delta,
                    batch_id=str(self._first_field_value(fields, settings.field_txn_batch_id, 'Batch ID', default='') or '') or None,
                    operator=str(self._first_field_value(fields, 'Initials', settings.field_txn_operator, 'Operator', default='') or '') or None,
                    note=str(self._first_field_value(fields, 'Notes', settings.field_txn_note, 'Note', default='') or '') or None,
                    source=str(self._first_field_value(fields, settings.field_txn_source, 'Source', default='') or '') or None,
                )
            )
        txns.sort(key=lambda t: self._transaction_sort_value(t.created_at), reverse=True)
        return txns[:limit]

    def _load_kits(self) -> tuple[dict[str, Kit], dict[str, list[KitComponent]]]:
        parts, _, _ = self._load_parts()
        part_by_record_id = {part.external_id: part for part in parts if part.external_id}

        raw_kits = self._list_all_records(
            settings.airtable_kits_table,
            fields=[settings.field_kit_code, settings.field_kit_name],
        )
        record_id_to_kit_code: dict[str, str] = {}
        kits_by_code: dict[str, Kit] = {}
        for record in raw_kits:
            fields = record.get('fields', {})
            code = str(fields.get(settings.field_kit_code, '')).strip()
            if not code:
                continue
            kit = Kit(
                code=code,
                name=str(fields.get(settings.field_kit_name, code)),
                external_id=record['id'],
                components=[],
            )
            kits_by_code[code] = kit
            record_id_to_kit_code[record['id']] = code

        raw_kit_items = self._list_all_records(
            settings.airtable_kit_items_table,
            fields=[settings.field_kit_item_kit, settings.field_kit_item_part, settings.field_kit_item_qty],
        )
        comps_by_code: dict[str, list[KitComponent]] = {code: [] for code in kits_by_code}
        for record in raw_kit_items:
            fields = record.get('fields', {})
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
        if action not in {'add', 'subtract', 'receive', 'undo_receive'}:
            raise ValidationError("Action must be add, subtract, receive, or undo_receive.")

    def _validate_quantity(self, quantity: int) -> None:
        if quantity < 1:
            raise ValidationError('Quantity must be at least 1.')

    def _build_transaction_fields_inventory_transactions(
        self,
        *,
        part_record_id: str,
        action: str,
        delta: int,
        operator: str,
        note: str,
        scanned_at: str,
        purchase_order_record_id: str | None = None,
        po_units_change: int | None = None,
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {
            'Timestamp': scanned_at,
            'Part': [part_record_id],
            'Transaction Type': self._transaction_type_label(action, purchase_order_record_id),
            'Quantity Change': delta,
            'Initials': operator.strip(),
            'Notes': note.strip(),
        }
        if purchase_order_record_id:
            fields['Purchase Order'] = [purchase_order_record_id]
        if po_units_change is not None and settings.field_txn_po_units_change:
            fields[settings.field_txn_po_units_change] = po_units_change
        return fields

    def _build_transaction_fields_legacy(
        self,
        *,
        part_record_id: str,
        sku: str,
        action: str,
        quantity: int,
        delta: int,
        batch_id: str,
        operator: str,
        note: str,
        source: str,
        scanned_at: str,
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        if settings.field_txn_part:
            fields[settings.field_txn_part] = [part_record_id]
        if settings.field_txn_sku:
            fields[settings.field_txn_sku] = sku
        if settings.field_txn_action:
            fields[settings.field_txn_action] = action
        if settings.field_txn_quantity:
            fields[settings.field_txn_quantity] = quantity
        if settings.field_txn_delta:
            fields[settings.field_txn_delta] = delta
        if settings.field_txn_batch_id:
            fields[settings.field_txn_batch_id] = batch_id
        if settings.field_txn_operator:
            fields[settings.field_txn_operator] = operator.strip()
        if settings.field_txn_note:
            fields[settings.field_txn_note] = note.strip()
        if settings.field_txn_source:
            fields[settings.field_txn_source] = source.strip()
        if settings.field_txn_scanned_at:
            fields[settings.field_txn_scanned_at] = scanned_at
        return fields

    def _create_transaction_record(
        self,
        *,
        part_record_id: str,
        sku: str,
        action: str,
        quantity: int,
        delta: int,
        batch_id: str,
        operator: str,
        note: str,
        source: str,
        scanned_at: str,
        purchase_order_record_id: str | None = None,
        po_units_change: int | None = None,
    ) -> None:
        if not self._transactions_table_configured():
            return
        field_sets: list[dict[str, Any]] = [
            self._build_transaction_fields_inventory_transactions(
                part_record_id=part_record_id,
                action=action,
                delta=delta,
                operator=operator,
                note=note,
                scanned_at=scanned_at,
                purchase_order_record_id=purchase_order_record_id,
                po_units_change=po_units_change,
            )
        ]
        legacy_fields = self._build_transaction_fields_legacy(
            part_record_id=part_record_id,
            sku=sku,
            action=action,
            quantity=quantity,
            delta=delta,
            batch_id=batch_id,
            operator=operator,
            note=note,
            source=source,
            scanned_at=scanned_at,
        )
        if legacy_fields != field_sets[0]:
            field_sets.append(legacy_fields)

        last_error: ValidationError | None = None
        for fields in field_sets:
            try:
                self._create_records(settings.airtable_transactions_table, [{'fields': fields}])
                return
            except ValidationError as exc:
                last_error = exc
                if self._is_missing_table_error(exc, settings.airtable_transactions_table):
                    raise
                continue

        if last_error is not None:
            raise last_error

    def _try_log_transaction(
        self,
        *,
        part_record_id: str,
        sku: str,
        action: str,
        quantity: int,
        delta: int,
        batch_id: str,
        operator: str,
        note: str,
        source: str,
        scanned_at: str,
        purchase_order_record_id: str | None = None,
        po_units_change: int | None = None,
    ) -> str | None:
        if not self._transactions_table_configured():
            return None
        try:
            self._create_transaction_record(
                part_record_id=part_record_id,
                sku=sku,
                action=action,
                quantity=quantity,
                delta=delta,
                batch_id=batch_id,
                operator=operator,
                note=note,
                source=source,
                scanned_at=scanned_at,
                purchase_order_record_id=purchase_order_record_id,
                po_units_change=po_units_change,
            )
            return None
        except ValidationError as exc:
            if self._is_missing_table_error(exc, settings.airtable_transactions_table):
                return f"transaction table '{settings.airtable_transactions_table}' is not configured"
            return str(exc)

    def _current_po_units_total(self, part_record_id: str, purchase_order_record_id: str) -> int:
        if not self._transactions_table_configured() or not purchase_order_record_id:
            return 0
        try:
            raw_txns = self._list_all_records(
                settings.airtable_transactions_table,
                fields=[
                    settings.field_txn_part,
                    settings.field_txn_purchase_order,
                    settings.field_txn_po_units_change,
                ],
            )
        except ValidationError as exc:
            if self._is_missing_table_error(exc, settings.airtable_transactions_table):
                return 0
            raise

        total = 0
        for record in raw_txns:
            fields = record.get('fields', {})
            part_ids = self._linked_record_ids(fields, settings.field_txn_part, 'Part')
            po_ids = self._linked_record_ids(fields, settings.field_txn_purchase_order, 'Purchase Order')
            if part_record_id not in part_ids or purchase_order_record_id not in po_ids:
                continue
            total += self._coerce_int(self._first_field_value(fields, settings.field_txn_po_units_change, 'PO Units Change', default=0))
        return total

    def apply_part_action(
        self,
        sku: str,
        action: str,
        quantity: int,
        operator: str = '',
        note: str = '',
        source: str = '',
        purchase_order_id: str = '',
        po_units: int | None = None,
    ) -> ActionResult:
        self._validate_action(action)
        self._validate_quantity(quantity)
        _, sku_to_id, sku_to_part = self._load_parts()
        if sku not in sku_to_id:
            raise NotFoundError(f"Part '{sku}' was not found in Airtable.")
        part = sku_to_part[sku]

        is_receive_mode = action in {'receive', 'undo_receive'}
        if is_receive_mode and not purchase_order_id:
            raise ValidationError('Select a Purchase Order to continue.')
        if is_receive_mode and (po_units is None or po_units < 1):
            raise ValidationError('PO Units must be at least 1.')

        delta = quantity if action in {'add', 'receive'} else -quantity

        signed_po_units_change = None
        if is_receive_mode and po_units is not None:
            signed_po_units_change = po_units if action == 'receive' else -po_units
            if action == 'undo_receive':
                current_po_total = self._current_po_units_total(sku_to_id[sku], purchase_order_id)
                if po_units > current_po_total:
                    raise ValidationError(
                        f'Cannot Undo Receive {po_units} PO units for {part.name}. Only {current_po_total} PO units are currently received for that purchase order.'
                    )

        new_qty = part.on_hand + delta
        if not self.allow_negative_stock and new_qty < 0:
            raise ValidationError(
                f'Cannot subtract {quantity} from {part.name}. Only {part.on_hand} currently on hand.'
            )

        if settings.airtable_sync_mode == 'transactions':
            batch_id = str(uuid.uuid4())
            scanned_at = self._now()
            self._create_transaction_record(
                part_record_id=sku_to_id[sku],
                sku=sku,
                action=action,
                quantity=quantity,
                delta=delta,
                batch_id=batch_id,
                operator=operator,
                note=note,
                source=source.strip() or f'qr:part:{sku}:{action}',
                scanned_at=scanned_at,
                purchase_order_record_id=purchase_order_id or None,
                po_units_change=signed_po_units_change,
            )
            updated = self.get_part(sku)
            return ActionResult(
                ok=True,
                message=f'Logged {action} of {quantity} x {updated.name}. Airtable will update on-hand via rollups/formulas.',
                batch_id=batch_id,
                touched_parts=[updated],
                transactions_created=1,
            )

        count_field = settings.field_part_on_hand or settings.field_part_starting_qty
        if not count_field:
            raise ValidationError('No Airtable count field is configured. Set FIELD_PART_ON_HAND or FIELD_PART_STARTING_QTY.')

        target_table = self._resolved_parts_table or settings.airtable_parts_table
        self._update_record(target_table, sku_to_id[sku], {count_field: new_qty})
        batch_id = str(uuid.uuid4())
        scanned_at = self._now()
        log_error = self._try_log_transaction(
            part_record_id=sku_to_id[sku],
            sku=sku,
            action=action,
            quantity=quantity,
            delta=delta,
            batch_id=batch_id,
            operator=operator,
            note=note,
            source=source.strip() or f'qr:part:{sku}:{action}',
            scanned_at=scanned_at,
            purchase_order_record_id=purchase_order_id or None,
            po_units_change=signed_po_units_change,
        )
        updated = Part(
            sku=part.sku,
            name=part.name,
            container_label=part.container_label,
            starting_qty=part.starting_qty,
            on_hand=new_qty,
            reorder_level=part.reorder_level,
            external_id=part.external_id,
            parts_per_po_unit=part.parts_per_po_unit,
        )
        message = f'Updated {updated.name}: {part.on_hand} -> {updated.on_hand}.'
        if log_error:
            message += f' Inventory count saved, but the transaction log was not written because {log_error}.'
        elif self._transactions_table_configured():
            message += ' Inventory count saved and transaction logged to Airtable.'
        else:
            message += ' Inventory count saved directly to Airtable.'
        return ActionResult(
            ok=True,
            message=message,
            batch_id=batch_id,
            touched_parts=[updated],
            transactions_created=0 if log_error or not self._transactions_table_configured() else 1,
        )

    def apply_kit_action(
        self,
        code: str,
        action: str,
        operator: str = '',
        note: str = '',
        source: str = '',
    ) -> ActionResult:
        self._validate_action(action)
        _, sku_to_id, _ = self._load_parts()
        kit = self.get_kit(code)
        if not kit.components:
            raise ValidationError(f"Kit '{kit.name}' has no components.")
        if not self.allow_negative_stock and action == 'subtract':
            shortages = [comp for comp in kit.components if comp.on_hand - comp.qty_per_kit < 0]
            if shortages:
                details = '; '.join(
                    f'{comp.part_name}: need {comp.qty_per_kit}, have {comp.on_hand}' for comp in shortages
                )
                raise ValidationError(f'Kit subtract blocked because stock would go negative. {details}')

        if settings.airtable_sync_mode == 'transactions':
            multiplier = 1 if action == 'add' else -1
            batch_id = str(uuid.uuid4())
            scanned_at = self._now()
            records: List[dict[str, Any]] = []
            for comp in kit.components:
                if comp.sku not in sku_to_id:
                    raise ValidationError(f"Part '{comp.sku}' is missing from the Airtable parts table.")
                records.append(
                    {
                        'fields': self._build_transaction_fields_inventory_transactions(
                            part_record_id=sku_to_id[comp.sku],
                            action=f'kit_{action}',
                            delta=multiplier * comp.qty_per_kit,
                            operator=operator,
                            note=note,
                            scanned_at=scanned_at,
                        )
                    }
                )
            self._create_records(settings.airtable_transactions_table, records)
            touched_parts = [self.get_part(comp.sku) for comp in kit.components]
            return ActionResult(
                ok=True,
                message=f"Logged {action} for kit {kit.name}. Airtable will update each linked part's on-hand value.",
                batch_id=batch_id,
                touched_parts=touched_parts,
                transactions_created=len(records),
            )

        multiplier = 1 if action == 'add' else -1
        batch_id = str(uuid.uuid4())
        scanned_at = self._now()
        touched_parts: list[Part] = []
        log_failures: list[str] = []
        tx_count = 0
        count_field = settings.field_part_on_hand or settings.field_part_starting_qty
        if not count_field:
            raise ValidationError('No Airtable count field is configured. Set FIELD_PART_ON_HAND or FIELD_PART_STARTING_QTY.')
        for comp in kit.components:
            record_id = sku_to_id.get(comp.sku)
            if not record_id:
                raise ValidationError(f"Part '{comp.sku}' is missing from the Airtable parts table.")
            new_qty = comp.on_hand + (multiplier * comp.qty_per_kit)
            target_table = self._resolved_parts_table or settings.airtable_parts_table
            self._update_record(target_table, record_id, {count_field: new_qty})
            touched_parts.append(
                Part(
                    sku=comp.sku,
                    name=comp.part_name,
                    container_label='',
                    starting_qty=0,
                    on_hand=new_qty,
                    reorder_level=0,
                    external_id=record_id,
                )
            )
            log_error = self._try_log_transaction(
                part_record_id=record_id,
                sku=comp.sku,
                action=f'kit_{action}',
                quantity=comp.qty_per_kit,
                delta=multiplier * comp.qty_per_kit,
                batch_id=batch_id,
                operator=operator,
                note=note,
                source=source.strip() or f'qr:kit:{code}:{action}',
                scanned_at=scanned_at,
            )
            if log_error:
                log_failures.append(f'{comp.part_name}: {log_error}')
            elif self._transactions_table_configured():
                tx_count += 1

        message = f'Updated {len(touched_parts)} BOM line items for kit {kit.name}.'
        if log_failures:
            message += ' Inventory counts were saved, but some transaction log entries were skipped: ' + '; '.join(log_failures)
        elif self._transactions_table_configured():
            message += ' Inventory counts were saved and transaction log entries were created.'
        else:
            message += ' Inventory counts were saved directly to Airtable.'
        return ActionResult(
            ok=True,
            message=message,
            batch_id=batch_id,
            touched_parts=touched_parts,
            transactions_created=tx_count,
        )


def build_airtable_store() -> AirtableStore:
    return AirtableStore(
        pat=settings.airtable_pat,
        base_id=settings.airtable_base_id,
        allow_negative_stock=settings.allow_negative_stock,
    )
