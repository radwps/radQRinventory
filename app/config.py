from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if load_dotenv:
    load_dotenv(PROJECT_ROOT / '.env')


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}

def _app_variant() -> str:
    return os.getenv("APP_VARIANT", "live").strip().lower()

def _header_prefix() -> str:
    return "QA Version - " if _app_variant() == "qa" else ""

def _header_bg_color() -> str:
    # pick whatever QA color you like
    return "#ffa500" if _app_variant() == "qa" else "#0f172a"

@dataclass(frozen=True)
class Settings:
    app_title: str = os.getenv('APP_TITLE', 'RAD Box QR Inventory')
    public_base_url: str = (os.getenv('PUBLIC_BASE_URL') or os.getenv('RENDER_EXTERNAL_URL') or '').strip()
    sku_prefix: str = os.getenv('SKU_PREFIX', '').strip()
    store_mode: str = os.getenv('STORE_MODE', 'mock').strip().lower()
    allow_negative_stock: bool = _as_bool(os.getenv('ALLOW_NEGATIVE_STOCK'), False)
    enable_kits: bool = _as_bool(os.getenv('ENABLE_KITS'), False)

    app_variant: str = _app_variant()
    header_prefix: str = _header_prefix()
    header_bg_color: str = _header_bg_color()

    project_root: Path = PROJECT_ROOT
    mock_db_path: Path = Path(os.getenv('MOCK_DB_PATH', str(project_root / 'demo_data' / 'radbox_inventory.db')))
    seed_file: Path = Path(os.getenv('SEED_FILE', str(project_root / 'demo_data' / 'seed.json')))

    airtable_pat: str = os.getenv('AIRTABLE_PAT', '')
    airtable_base_id: str = os.getenv('AIRTABLE_BASE_ID', '')
    airtable_parts_table: str = os.getenv('AIRTABLE_PARTS_TABLE', 'Inventory').strip()
    airtable_transactions_table: str = os.getenv('AIRTABLE_TRANSACTIONS_TABLE', 'Inventory Transactions').strip()
    airtable_kits_table: str = os.getenv('AIRTABLE_KITS_TABLE', 'Kits').strip()
    airtable_kit_items_table: str = os.getenv('AIRTABLE_KIT_ITEMS_TABLE', 'Kit Items').strip()
    airtable_sync_mode: str = os.getenv('AIRTABLE_SYNC_MODE', 'direct_count').strip().lower()
    airtable_filter_to_catalog: bool = _as_bool(os.getenv('AIRTABLE_FILTER_TO_CATALOG'), True)
    airtable_log_transactions: bool = _as_bool(os.getenv('AIRTABLE_LOG_TRANSACTIONS'), False)

    field_part_sku: str = os.getenv('FIELD_PART_SKU', '').strip()
    field_part_name: str = os.getenv('FIELD_PART_NAME', 'Line Item Name').strip()
    field_part_container: str = os.getenv('FIELD_PART_CONTAINER', '').strip()
    field_part_starting_qty: str = os.getenv('FIELD_PART_STARTING_QTY', '').strip()
    field_part_on_hand: str = os.getenv('FIELD_PART_ON_HAND', 'Quantity In Stock').strip()
    field_part_reorder_level: str = os.getenv('FIELD_PART_REORDER_LEVEL', '').strip()
    field_part_parts_per_po_unit: str = os.getenv('FIELD_PART_PARTS_PER_PO_UNIT', 'Parts per PO Unit').strip()
    field_part_parts_per_rad_unit: str = os.getenv('FIELD_PART_PARTS_PER_RAD_UNIT', 'Parts per RAD Unit').strip()

    field_txn_part: str = os.getenv('FIELD_TXN_PART', 'Part').strip()
    field_txn_sku: str = os.getenv('FIELD_TXN_SKU', 'SKU').strip()
    field_txn_action: str = os.getenv('FIELD_TXN_ACTION', 'Action').strip()
    field_txn_quantity: str = os.getenv('FIELD_TXN_QUANTITY', 'Quantity').strip()
    field_txn_delta: str = os.getenv('FIELD_TXN_DELTA', 'Delta').strip()
    field_txn_batch_id: str = os.getenv('FIELD_TXN_BATCH_ID', 'Batch ID').strip()
    field_txn_operator: str = os.getenv('FIELD_TXN_OPERATOR', 'Operator').strip()
    field_txn_note: str = os.getenv('FIELD_TXN_NOTE', 'Note').strip()
    field_txn_source: str = os.getenv('FIELD_TXN_SOURCE', 'Source').strip()
    field_txn_scanned_at: str = os.getenv('FIELD_TXN_SCANNED_AT', 'Scanned At').strip()
    field_txn_purchase_order: str = os.getenv('FIELD_TXN_PURCHASE_ORDER', 'Purchase Order').strip()
    field_txn_po_units_change: str = os.getenv('FIELD_TXN_PO_UNITS_CHANGE', 'PO Units Change').strip()

    field_kit_code: str = os.getenv('FIELD_KIT_CODE', 'Kit Code').strip()
    field_kit_name: str = os.getenv('FIELD_KIT_NAME', 'Kit Name').strip()

    field_kit_item_kit: str = os.getenv('FIELD_KIT_ITEM_KIT', 'Kit').strip()
    field_kit_item_part: str = os.getenv('FIELD_KIT_ITEM_PART', 'Part').strip()
    field_kit_item_qty: str = os.getenv('FIELD_KIT_ITEM_QTY', 'Qty Per Kit').strip()


settings = Settings()


WHOLE_UNIT_BASE_CODE = 'WHOLE-RAD-BOX'


def runtime_sku(sku: str) -> str:
    prefix = (settings.sku_prefix or '').strip()
    if not sku:
        return sku
    if prefix and sku.startswith(prefix):
        return sku
    return f'{prefix}{sku}' if prefix else sku


def canonical_sku(sku: str) -> str:
    prefix = (settings.sku_prefix or '').strip()
    if prefix and sku.startswith(prefix):
        return sku[len(prefix):]
    return sku


def runtime_whole_unit_code() -> str:
    return runtime_sku(WHOLE_UNIT_BASE_CODE)
