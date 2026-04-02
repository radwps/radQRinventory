from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogEntry:
    sku: str
    display_name: str
    airtable_names: tuple[str, ...]


TARGET_PARTS: tuple[CatalogEntry, ...] = (
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


def normalize_part_name(value: str | None) -> str:
    text = (value or '').strip().lower()
    text = text.replace('&', 'and')
    text = text.replace('“', '"').replace('”', '"').replace('’', "'")
    text = text.replace('–', '-').replace('—', '-')
    text = text.replace('²', '2')
    text = re.sub(r'\s+', ' ', text)
    return text


_CATALOG_LOOKUP = {}
for entry in TARGET_PARTS:
    _CATALOG_LOOKUP[normalize_part_name(entry.display_name)] = entry
    for alias in entry.airtable_names:
        _CATALOG_LOOKUP[normalize_part_name(alias)] = entry


def find_catalog_entry(raw_name: str | None) -> CatalogEntry | None:
    return _CATALOG_LOOKUP.get(normalize_part_name(raw_name))


CATALOG_ORDER = {entry.sku: index for index, entry in enumerate(TARGET_PARTS)}


def catalog_sort_key(sku: str, fallback_name: str = '') -> tuple[int, str]:
    return (CATALOG_ORDER.get(sku, len(CATALOG_ORDER)), (fallback_name or '').lower())


CATALOG_BY_SKU = {entry.sku: entry for entry in TARGET_PARTS}
