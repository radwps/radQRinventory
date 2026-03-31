from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogEntry:
    sku: str
    display_name: str
    airtable_names: tuple[str, ...]


TARGET_PARTS: tuple[CatalogEntry, ...] = (
    CatalogEntry('RAD-MP3-PLAYER', 'MP3 Player', ('MP3 Player',)),
    CatalogEntry('RAD-SD-8GB', '8 GB SD Card', ('8 GB SD Card', '8 GB SD Card (for MP3)')),
    CatalogEntry('RAD-PAM8610-AMP', 'HiLetgo PAM8610 Mini Stereo AMP', ('HiLetgo PAM8610 Mini Stereo AMP',)),
    CatalogEntry(
        'RAD-AMP-KNOBS',
        'Potentiometer Control Knobs for Amp',
        ('Potentiometer Control Knobs for Amp', '30 PCS 6mm Potentiometer Control Knobs for Amp'),
    ),
    CatalogEntry('RAD-12V-5V-USBC', '12V to 5V Converter USB-C', ('12V to 5V Converter USB-C', '12v to 5v Converter USB-C')),
    CatalogEntry(
        'RAD-PWR-DIST-1X12',
        '1x12 Position Power Distribution Board',
        ('1x12 Position Power Distribution Board', '1X 12 Position Power Distribution Board'),
    ),
    CatalogEntry('RAD-DC-BARREL-GLAND', 'DC Barrel Glands', ('DC Barrel Glands',)),
    CatalogEntry('RAD-CNLINKO-USBC', 'CNLINKO USB-C Gland', ('CNLINKO USB-C Gland',)),
    CatalogEntry(
        'RAD-LP12-4PIN-1M',
        'CNLINKO LP12 4-Pin Circular Connector with 1 Meter Cable',
        ('CNLINKO LP12 4-Pin Circular Connector with 1 Meter Cable',),
    ),
    CatalogEntry('RAD-AUDIO-GLAND', 'Audio Gland', ('Audio Gland',)),
    CatalogEntry(
        'RAD-AUDIO-JUMP-6IN',
        '6" Audio Jump Cable Amp & Out',
        ('6" Audio Jump Cable Amp & Out', '6" audio jump cable Amp & Out'),
    ),
    CatalogEntry(
        'RAD-12V-5A-PIGTAIL-M',
        '12V 5A DC Power Pigtail Cord Male Plug Connectors',
        (
            '12V 5A DC Power Pigtail Cord Male Plug Connectors',
            '20-Pack 12V 5A DC Power Pigtail Cord Male Plug Connectors, 5.5mm x 2.1mm',
        ),
    ),
)


def normalize_part_name(value: str | None) -> str:
    text = (value or '').strip().lower()
    text = text.replace('&', 'and')
    text = text.replace('“', '"').replace('”', '"').replace('’', "'")
    text = re.sub(r'\s+', ' ', text)
    return text


_CATALOG_LOOKUP = {}
for entry in TARGET_PARTS:
    _CATALOG_LOOKUP[normalize_part_name(entry.display_name)] = entry
    for alias in entry.airtable_names:
        _CATALOG_LOOKUP[normalize_part_name(alias)] = entry


def find_catalog_entry(raw_name: str | None) -> CatalogEntry | None:
    return _CATALOG_LOOKUP.get(normalize_part_name(raw_name))


CATALOG_BY_SKU = {entry.sku: entry for entry in TARGET_PARTS}
