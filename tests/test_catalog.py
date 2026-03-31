from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.part_catalog import find_catalog_entry


def test_catalog_matches_bom_variants() -> None:
    assert find_catalog_entry('8 GB SD Card (for MP3)').sku == 'RAD-SD-8GB'
    assert find_catalog_entry('30 PCS 6mm Potentiometer Control Knobs for Amp').sku == 'RAD-AMP-KNOBS'
    assert find_catalog_entry('12v to 5v Converter USB-C').sku == 'RAD-12V-5V-USBC'
    assert find_catalog_entry('1X 12 Position Power Distribution Board').sku == 'RAD-PWR-DIST-1X12'
    assert find_catalog_entry('6" audio jump cable Amp & Out').sku == 'RAD-AUDIO-JUMP-6IN'
