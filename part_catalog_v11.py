from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, TypeVar


@dataclass(frozen=True)
class CatalogEntry:
    sku: str
    display_name: str
    airtable_names: tuple[str, ...]


DEFAULT_TARGET_PARTS: tuple[CatalogEntry, ...] = (
    CatalogEntry('RAD-IP67-JBOX', 'IP67 Waterproof Junction Box (11.8x7.9x6.3)', ('IP67 Waterproof Junction Box (11.8x7.9x6.3)', 'IP67 Waterproof Junction Box (check if 7.1”!)')),
    CatalogEntry('RAD-CWT5015-RTU', '4G RTU Remote Terminal Unit CWT5015', ('4G RTU Remote Terminal Unit CWT5015', 'CWT5015 4G RTU Remote Terminal Unit CWT5015')),
    CatalogEntry('RAD-MP3-PLAYER', 'MP3 Player', ('MP3 Player',)),
    CatalogEntry('RAD-SD-8GB', '8 GB SD Card (for MP3)', ('8 GB SD Card (for MP3)', '8 GB SD Card')),
    CatalogEntry('RAD-PAM8610-AMP', 'HiLetgo PAM8610 Mini Stereo AMP', ('HiLetgo PAM8610 Mini Stereo AMP',)),
    CatalogEntry('RAD-JUMPER-CAPS-254', '100pcs California JOS 2.54mm Black Jumper Caps', ('100pcs California JOS 2.54mm Black Jumper Caps',)),
    CatalogEntry('RAD-AMP-HOUSING-3D', '3d Housing for Amp (Filament)', ('3d Housing for Amp (Filament)', '3d Housing for Amp')),
    CatalogEntry('RAD-AMP-KNOBS', '30 PCS 6mm Potentiometer Control Knobs for Amp', ('30 PCS 6mm Potentiometer Control Knobs for Amp', 'Potentiometer Control Knobs for Amp')),
    CatalogEntry('RAD-12V-5V-USBC', '12v to 5v Converter USB-C', ('12v to 5v Converter USB-C', '12V to 5V Converter USB-C')),
    CatalogEntry('RAD-PWR-DIST-1X12', '1X 12 Position Power Distribution Board', ('1X 12 Position Power Distribution Board', '1x12 Position Power Distribution Board')),
    CatalogEntry('RAD-DC-BARREL-GLAND', 'DC Barrel Glands', ('DC Barrel Glands',)),
    CatalogEntry('RAD-CNLINKO-USBC', 'CNLINKO USB-C Gland', ('CNLINKO USB-C Gland',)),
    CatalogEntry('RAD-LP12-4PIN-1M', 'CNLINKO LP12 4-Pin Circular Connector with 1 Meter Cable', ('CNLINKO LP12 4-Pin Circular Connector with 1 Meter Cable',)),
    CatalogEntry('RAD-AUDIO-GLAND', 'Audio Gland', ('Audio Gland',)),
    CatalogEntry('RAD-STANDOFFS-MP3-AMP', 'Standoffs for MP3 Player, Amp, Power Distribution (50 pcs)', ('Standoffs for MP3 Player, Amp, Power Distribution (50 pcs)',)),
    CatalogEntry('RAD-SCREWS-ST-19MM', '1" Self Tapping Screws (250 pcs) 19mm', ('1" Self Tapping Screws (250 pcs) 19mm',)),
    CatalogEntry('RAD-SCREWS-ST-12MM', '1" Self Tapping Screws (250 pcs) 12mm', ('1" Self Tapping Screws (250 pcs) 12mm',)),
    CatalogEntry('RAD-M3X6-SS', 'M3 x 6 mm 304 Stainless Steel Screws', ('M3 x 6 mm 304 Stainless Steel Screws',)),
    CatalogEntry('RAD-M35X16-HEX', '100 Pcs M3.5x16mm Stainless Steel Hex', ('100 Pcs M3.5x16mm Stainless Steel Hex',)),
    CatalogEntry('RAD-WIRE-CONN-1IN3OUT', '10Pcs Mini Electrical Wire Connectors 1in 3 out', ('10Pcs Mini Electrical Wire Connectors 1in 3 out',)),
    CatalogEntry('RAD-WIRE-BUTT-2216', '22 - 16 awg wire butt connectors – MP3', ('22 - 16 awg wire butt connectors – MP3',)),
    CatalogEntry('RAD-HEATSHRINK-433X4', 'Heat Shrink Tube Wire (433mhz x4)', ('Heat Shrink Tube Wire (433mhz x4)',)),
    CatalogEntry('RAD-AUDIO-JUMP-6IN', '6" audio jump cable Amp & Out', ('6" audio jump cable Amp & Out', '6" Audio Jump Cable Amp & Out')),
    CatalogEntry('RAD-12V-5A-PIGTAIL-M', '20-Pack 12V 5A DC Power Pigtail Cord Male Plug Connectors, 5.5mm x 2.1mm', ('20-Pack 12V 5A DC Power Pigtail Cord Male Plug Connectors, 5.5mm x 2.1mm', '12V 5A DC Power Pigtail Cord Male Plug Connectors')),
    CatalogEntry('RAD-FERRULE-AWG20-075', '1000PCS Wire Ferrule Connectors AWG20 0.75mm²', ('1000PCS Wire Ferrule Connectors AWG20 0.75mm²',)),
    CatalogEntry('RAD-AWG22-05', '1000 PCS AWG 22/0.5mm²', ('1000 PCS AWG 22/0.5mm²',)),
    CatalogEntry('RAD-WIRE-18AWG-SPOOL', '18 AWG Stranded Wire Spool', ('18 AWG Stranded Wire Spool',)),
    CatalogEntry('RAD-OUTDOOR-SPEAKER', 'Outdoor Speaker', ('Outdoor Speaker',)),
    CatalogEntry('RAD-35MM-SPKR-PIGTAIL', '3.5mm 1/8" to Speaker Wire, 2-Pack 10FT 3.5mm TS Mono Male Plug to Bare Wire Pigtail', ('3.5mm 1/8" to Speaker Wire, 2-Pack 10FT 3.5mm TS Mono Male Plug to Bare Wire Pigtail',)),
    CatalogEntry('RAD-LED-STRIP-33FT', 'LED Strip(33Ft Smart Globe String Lights, 50 Dimmable RGB)', ('LED Strip(33Ft Smart Globe String Lights, 50 Dimmable RGB)',)),
    CatalogEntry('RAD-USBF-USBCF-ADAPT', '10 USB Female to USB C Female Adapter', ('10 USB Female to USB C Female Adapter',)),
    CatalogEntry('RAD-WATERPROOF-GLAND', 'Waterproof Cable Gland', ('Waterproof Cable Gland',)),
    CatalogEntry('RAD-SPARKAWAY-PLATE', 'Spark Away Voltage Plate w/ Shipping', ('Spark Away Voltage Plate w/ Shipping',)),
    CatalogEntry('RAD-SPARKAWAY-HOUSING', 'Spark Away Housing (light fixture)', ('Spark Away Housing (light fixture)',)),
    CatalogEntry('RAD-SPARKAWAY-STAKE', 'Metal Stake for Spark-away', ('Metal Stake for Spark-away',)),
    CatalogEntry('RAD-SPARKAWAY-POLE', 'Spark Away Pole Extension', ('Spark Away Pole Extension',)),
    CatalogEntry('RAD-SPARKAWAY-ADAPTER', 'Pipe Adapter for Spark Away', ('Pipe Adapter for Spark Away',)),
    CatalogEntry('RAD-DC-CABLE-5M', '5m DC power cable', ('5m DC power cable',)),
    CatalogEntry('RAD-SOLAR-WILDGAME-D20', 'Wildgame D20-18 20w Solar w/ Battery & 1m Cable, mount, shipping to US', ('Wildgame D20-18 20w Solar w/ Battery & 1m Cable, mount, shipping to US',)),
    CatalogEntry('RAD-SCENT-DISPENSER', 'Scent Dispenser', ('Scent Dispenser',)),
    CatalogEntry('RAD-SCENT-CABLES-ADAPTER', 'Scent Dispenser Cables & External Power adaptor', ('Scent Dispenser Cables & External Power adaptor',)),
    CatalogEntry('RAD-SHIPPING-CUSTOMS', 'Est. Shipping & Customs', ('Est. Shipping & Customs',)),
    CatalogEntry('RAD-SIM-DATA-PLAN', 'SIM Card / Data Plan', ('SIM Card / Data Plan',)),
)


T = TypeVar('T')


def normalize_part_name(value: str | None) -> str:
    text = (value or '').strip().lower()
    text = text.replace('&', 'and')
    text = text.replace('“', '"').replace('”', '"').replace('’', "'")
    text = text.replace('–', '-').replace('—', '-')
    text = text.replace('²', '2')
    text = re.sub(r'\s+', ' ', text)
    return text


def _catalog_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _catalog_order_csv_paths() -> tuple[Path, ...]:
    root = _catalog_root()
    return (
        root / 'airtable_import' / 'inventory_mapping.csv',
        root / 'airtable_import' / 'bom_line_items_mapping.csv',
        root / 'airtable_import' / 'parts_import.csv',
    )


def _split_aliases(value: str | None) -> tuple[str, ...]:
    text = (value or '').strip()
    if not text:
        return ()
    parts = re.split(r'[|\r\n]+', text)
    return tuple(part.strip() for part in parts if part and part.strip())


def _dedupe_preserve_order(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = normalize_part_name(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(value.strip())
    return tuple(ordered)


def _load_catalog_entries_from_csv() -> tuple[CatalogEntry, ...]:
    for path in _catalog_order_csv_paths():
        if not path.exists():
            continue
        with path.open('r', encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            if not fieldnames:
                continue

            def first_present(*names: str) -> str | None:
                return next((name for name in names if name in fieldnames), None)

            sku_field = first_present('App SKU', 'SKU', 'sku')
            display_field = first_present('App Display Name', 'Display Name', 'Line Item Name', 'Inventory Name Used', 'Part')
            inventory_name_field = first_present('Inventory Name Used', 'Line Item Name', 'Part')
            alternate_field = first_present('Accepted Alternate Match', 'Accepted Alternate Matches', 'Alternate Match', 'Alternate Matches')
            if not sku_field or not display_field:
                continue

            entries: list[CatalogEntry] = []
            for row in reader:
                sku = (row.get(sku_field) or '').strip()
                if not sku:
                    continue
                display_name = (row.get(display_field) or '').strip()
                inventory_name = (row.get(inventory_name_field) or '').strip() if inventory_name_field else ''
                if not display_name:
                    display_name = inventory_name or sku
                alias_candidates: list[str] = [display_name]
                if inventory_name:
                    alias_candidates.append(inventory_name)
                if alternate_field:
                    alias_candidates.extend(_split_aliases(row.get(alternate_field)))
                entries.append(
                    CatalogEntry(
                        sku=sku,
                        display_name=display_name,
                        airtable_names=_dedupe_preserve_order(alias_candidates),
                    )
                )
            if entries:
                return tuple(entries)
    return ()


TARGET_PARTS: tuple[CatalogEntry, ...] = _load_catalog_entries_from_csv() or DEFAULT_TARGET_PARTS


_CATALOG_LOOKUP: dict[str, CatalogEntry] = {}
CATALOG_NAME_ORDER: dict[str, int] = {}
for index, entry in enumerate(TARGET_PARTS):
    CATALOG_NAME_ORDER[normalize_part_name(entry.display_name)] = index
    _CATALOG_LOOKUP[normalize_part_name(entry.display_name)] = entry
    for alias in entry.airtable_names:
        normalized_alias = normalize_part_name(alias)
        CATALOG_NAME_ORDER[normalized_alias] = index
        _CATALOG_LOOKUP[normalized_alias] = entry


CATALOG_ORDER = {entry.sku: index for index, entry in enumerate(TARGET_PARTS)}


def find_catalog_entry(raw_name: str | None) -> CatalogEntry | None:
    return _CATALOG_LOOKUP.get(normalize_part_name(raw_name))


def catalog_position(sku: str, fallback_name: str = '') -> int:
    if sku in CATALOG_ORDER:
        return CATALOG_ORDER[sku]
    normalized_name = normalize_part_name(fallback_name)
    if normalized_name in CATALOG_NAME_ORDER:
        return CATALOG_NAME_ORDER[normalized_name]
    return len(CATALOG_ORDER)


def catalog_sort_key(sku: str, fallback_name: str = '') -> tuple[int, str]:
    return (catalog_position(sku, fallback_name), (fallback_name or '').lower())


def sort_in_catalog_order(items: Sequence[T], *, get_sku, get_name=None) -> list[T]:
    indexed_items = list(enumerate(items))

    def sort_key(pair: tuple[int, T]) -> tuple[int, int]:
        original_index, item = pair
        sku = get_sku(item)
        name = get_name(item) if get_name else ''
        position = catalog_position(sku, name)
        if position >= len(CATALOG_ORDER):
            position = len(CATALOG_ORDER) + original_index
        return (position, original_index)

    indexed_items.sort(key=sort_key)
    return [item for _, item in indexed_items]


CATALOG_BY_SKU = {entry.sku: entry for entry in TARGET_PARTS}
