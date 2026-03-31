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


@dataclass(frozen=True)
class Settings:
    app_title: str = os.getenv('APP_TITLE', 'RAD Box QR Inventory')
    public_base_url: str = (os.getenv('PUBLIC_BASE_URL') or os.getenv('RENDER_EXTERNAL_URL') or '').strip()
    store_mode: str = os.getenv('STORE_MODE', 'mock').strip().lower()
    allow_negative_stock: bool = os.getenv('ALLOW_NEGATIVE_STOCK', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}
    enable_kits: bool = os.getenv('ENABLE_KITS', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}

    project_root: Path = PROJECT_ROOT
    mock_db_path: Path = Path(os.getenv('MOCK_DB_PATH', str(project_root / 'demo_data' / 'radbox_inventory.db')))
    seed_file: Path = Path(os.getenv('SEED_FILE', str(project_root / 'demo_data' / 'seed.json')))

    airtable_pat: str = os.getenv('AIRTABLE_PAT', '')
    airtable_base_id: str = os.getenv('AIRTABLE_BASE_ID', '')
    airtable_parts_table: str = os.getenv('AIRTABLE_PARTS_TABLE', 'Parts')
    airtable_transactions_table: str = os.getenv('AIRTABLE_TRANSACTIONS_TABLE', 'Transactions')
    airtable_kits_table: str = os.getenv('AIRTABLE_KITS_TABLE', 'Kits')
    airtable_kit_items_table: str = os.getenv('AIRTABLE_KIT_ITEMS_TABLE', 'Kit Items')

    field_part_sku: str = os.getenv('FIELD_PART_SKU', 'SKU')
    field_part_name: str = os.getenv('FIELD_PART_NAME', 'Part Name')
    field_part_container: str = os.getenv('FIELD_PART_CONTAINER', 'Container Label')
    field_part_starting_qty: str = os.getenv('FIELD_PART_STARTING_QTY', 'Starting Qty')
    field_part_on_hand: str = os.getenv('FIELD_PART_ON_HAND', 'On Hand')
    field_part_reorder_level: str = os.getenv('FIELD_PART_REORDER_LEVEL', 'Reorder Level')

    field_txn_part: str = os.getenv('FIELD_TXN_PART', 'Part')
    field_txn_sku: str = os.getenv('FIELD_TXN_SKU', 'SKU')
    field_txn_action: str = os.getenv('FIELD_TXN_ACTION', 'Action')
    field_txn_quantity: str = os.getenv('FIELD_TXN_QUANTITY', 'Quantity')
    field_txn_delta: str = os.getenv('FIELD_TXN_DELTA', 'Delta')
    field_txn_batch_id: str = os.getenv('FIELD_TXN_BATCH_ID', 'Batch ID')
    field_txn_operator: str = os.getenv('FIELD_TXN_OPERATOR', 'Operator')
    field_txn_note: str = os.getenv('FIELD_TXN_NOTE', 'Note')
    field_txn_source: str = os.getenv('FIELD_TXN_SOURCE', 'Source')
    field_txn_scanned_at: str = os.getenv('FIELD_TXN_SCANNED_AT', 'Scanned At')

    field_kit_code: str = os.getenv('FIELD_KIT_CODE', 'Kit Code')
    field_kit_name: str = os.getenv('FIELD_KIT_NAME', 'Kit Name')

    field_kit_item_kit: str = os.getenv('FIELD_KIT_ITEM_KIT', 'Kit')
    field_kit_item_part: str = os.getenv('FIELD_KIT_ITEM_PART', 'Part')
    field_kit_item_qty: str = os.getenv('FIELD_KIT_ITEM_QTY', 'Qty Per Kit')


settings = Settings()
