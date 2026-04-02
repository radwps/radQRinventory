from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.airtable_store import AirtableStore
from app.config import settings
from app.store import ValidationError


class FakeAirtableStore(AirtableStore):
    def __init__(self):
        super().__init__(pat='pat_test', base_id='app_test')
        self.updated = []

    def _list_all_records(self, table: str, fields=None):
        if table == 'BOM Line Items':
            raise ValidationError('Airtable API error on BOM Line Items: Could not find table BOM Line Items')
        if table == 'Inventory':
            return [
                {
                    'id': 'rec123',
                    'fields': {
                        'Line Item Name': '4G RTU Remote Terminal Unit CWT5015',
                        'Quantity In Stock': 2,
                    },
                }
            ]
        return []

    def _update_record(self, table: str, record_id: str, fields):
        self.updated.append((table, record_id, fields))



def test_falls_back_to_inventory_table_and_uses_it_for_updates() -> None:
    original = settings.airtable_parts_table
    object.__setattr__(settings, 'airtable_parts_table', 'BOM Line Items')
    try:
        store = FakeAirtableStore()
        part = store.get_part('RAD-CWT5015-RTU')
        assert part.name == '4G RTU Remote Terminal Unit CWT5015'
        result = store.apply_part_action('RAD-CWT5015-RTU', 'add', 3, operator='RB')
        assert result.ok is True
        assert store.updated == [('Inventory', 'rec123', {'Quantity In Stock': 5})]
    finally:
        object.__setattr__(settings, 'airtable_parts_table', original)
