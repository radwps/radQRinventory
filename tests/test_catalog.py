from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.part_catalog import TARGET_PARTS, catalog_sort_key, find_catalog_entry


def test_catalog_matches_bom_variants_and_preserves_existing_skus() -> None:
    assert len(TARGET_PARTS) == 43
    assert find_catalog_entry('MP3 Player').sku == 'RAD-MP3-PLAYER'
    assert find_catalog_entry('8 GB SD Card (for MP3)').sku == 'RAD-SD-8GB'
    assert find_catalog_entry('8 GB SD Card').sku == 'RAD-SD-8GB'
    assert find_catalog_entry('30 PCS 6mm Potentiometer Control Knobs for Amp').sku == 'RAD-AMP-KNOBS'
    assert find_catalog_entry('Potentiometer Control Knobs for Amp').sku == 'RAD-AMP-KNOBS'
    assert find_catalog_entry('12v to 5v Converter USB-C').sku == 'RAD-12V-5V-USBC'
    assert find_catalog_entry('12V to 5V Converter USB-C').sku == 'RAD-12V-5V-USBC'
    assert find_catalog_entry('1X 12 Position Power Distribution Board').sku == 'RAD-PWR-DIST-1X12'
    assert find_catalog_entry('1x12 Position Power Distribution Board').sku == 'RAD-PWR-DIST-1X12'
    assert find_catalog_entry('6" audio jump cable Amp & Out').sku == 'RAD-AUDIO-JUMP-6IN'
    assert find_catalog_entry('6" Audio Jump Cable Amp & Out').sku == 'RAD-AUDIO-JUMP-6IN'
    assert find_catalog_entry('20-Pack 12V 5A DC Power Pigtail Cord Male Plug Connectors, 5.5mm x 2.1mm').sku == 'RAD-12V-5A-PIGTAIL-M'
    assert find_catalog_entry('12V 5A DC Power Pigtail Cord Male Plug Connectors').sku == 'RAD-12V-5A-PIGTAIL-M'
    assert find_catalog_entry('SIM Card / Data Plan').sku == 'RAD-SIM-DATA-PLAN'


def test_catalog_sort_key_preserves_csv_pdf_order() -> None:
    ordered = sorted(TARGET_PARTS, key=lambda entry: catalog_sort_key(entry.sku, entry.display_name))
    assert [entry.display_name for entry in ordered[:5]] == [
        'IP67 Waterproof Junction Box (check if 7.1”!)',
        'CWT5015 4G RTU Remote Terminal Unit CWT5015',
        'MP3 Player',
        '8 GB SD Card (for MP3)',
        'HiLetgo PAM8610 Mini Stereo AMP',
    ]
    assert ordered[-1].display_name == 'SIM Card / Data Plan'
