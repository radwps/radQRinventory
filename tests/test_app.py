from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import STORE, app


client = TestClient(app)
PRIMARY_SKU = 'RAD-MP3-PLAYER'
PRIMARY_NAME = 'MP3 Player'


def setup_function() -> None:
    if hasattr(STORE, 'reset_from_seed'):
        STORE.reset_from_seed()


def test_dashboard_loads() -> None:
    response = client.get('/')
    assert response.status_code == 200
    assert 'RAD Box QR Inventory' in response.text
    assert PRIMARY_NAME in response.text
    assert 'Whole-box kit labels are currently disabled' in response.text


def test_generic_part_scan_page_loads() -> None:
    response = client.get(f'/scan/part/{PRIMARY_SKU}')
    assert response.status_code == 200
    assert f'Update {PRIMARY_NAME}' in response.text
    assert 'Add inventory' in response.text
    assert 'Subtract inventory' in response.text


def test_part_subtract_creates_transaction_and_updates_quantity() -> None:
    before = STORE.get_part(PRIMARY_SKU).on_hand
    response = client.post(f'/scan/part/{PRIMARY_SKU}', data={'action': 'add', 'quantity': '2', 'operator': 'RB'})
    assert response.status_code == 200
    after = STORE.get_part(PRIMARY_SKU).on_hand
    assert after == before + 2
    transactions = STORE.list_transactions(limit=5)
    assert transactions[0].sku == PRIMARY_SKU
    assert transactions[0].delta == 2


def test_legacy_part_route_still_works() -> None:
    before = STORE.get_part(PRIMARY_SKU).on_hand
    response = client.post(f'/scan/part/{PRIMARY_SKU}/subtract', data={'quantity': '1', 'operator': 'RB'})
    assert response.status_code == 400
    after = STORE.get_part(PRIMARY_SKU).on_hand
    assert after == before


def test_labels_page_uses_single_qr_per_part_and_90x30_note() -> None:
    response = client.get('/labels?base_url=https://example.com')
    assert response.status_code == 200
    assert 'Printable QR labels (90 mm x 30 mm)' in response.text
    assert 'Scan to add or subtract' in response.text
    assert 'Whole-box subtract labels' not in response.text
    assert '<code>https://example.com</code>' in response.text
    assert response.text.count('Scan to add or subtract') >= 43


def test_mock_seed_contains_all_pdf_line_items() -> None:
    parts = STORE.list_parts()
    assert len(parts) == 43
    assert all(part.on_hand == 0 for part in parts)
    assert any(part.sku == 'RAD-SIM-DATA-PLAN' for part in parts)
