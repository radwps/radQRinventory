# RAD Box QR Inventory Prototype

This build is configured for the existing Airtable base **RAD Operations Tracker (LIVE)** using the **BOM Line Items** table structure you exported.

## What this build now does

- Uses **BOM Line Items** as the Airtable inventory source table.
- Reads the part name from **Line Item Name**.
- Reads and writes inventory counts directly to **Quantity In Stock**.
- Filters Airtable to the full set of **43 nonblank BOM line items** found in your export.
- Uses one QR code per part container.
- Prints labels at **90 mm wide x 30 mm tall**.
- Keeps the mock/demo mode intact for offline testing.

## BOM field mapping used by this build

- Table: `BOM Line Items`
- Part name field: `Line Item Name`
- Count field: `Quantity In Stock`
- QR/scan identifiers: the app uses stable internal SKUs such as `RAD-MP3-PLAYER`, mapped to the matching BOM line item

## Existing QR codes preserved

For the items that were already in the app, the same SKUs were kept so previously printed QR codes still resolve to the same scan pages.

Examples:

- `RAD-MP3-PLAYER`
- `RAD-SD-8GB`
- `RAD-PAM8610-AMP`
- `RAD-AMP-KNOBS`
- `RAD-12V-5V-USBC`
- `RAD-PWR-DIST-1X12`
- `RAD-AUDIO-JUMP-6IN`
- `RAD-12V-5A-PIGTAIL-M`

## Important behavior note about counts

- In **mock/demo mode**, all seeded counts are reset to `0`.
- In **Airtable mode**, the app shows whatever is currently stored in Airtable under `Quantity In Stock`.
- Updating the code alone does **not** zero out live Airtable records. If you want the live base reset to zero, update the `Quantity In Stock` values in Airtable as well.

## Local run

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

## Local Airtable mode

Copy `.env.example` to `.env`, then set at minimum:

```env
STORE_MODE=airtable
AIRTABLE_PAT=pat_xxx
AIRTABLE_BASE_ID=app_xxx
```

In this build, the rest of the Airtable mapping defaults already point at the BOM structure.

## Optional transaction log table

If you later want a log in Airtable too, create a table such as `Inventory Transactions` and keep or adjust the default field names in `.env.example`.

Recommended fields:

- `Part` (linked record to BOM Line Items, optional)
- `SKU`
- `Action`
- `Quantity`
- `Delta`
- `Batch ID`
- `Operator`
- `Note`
- `Source`
- `Scanned At`

Then enable it with:

```env
AIRTABLE_LOG_TRANSACTIONS=true
AIRTABLE_TRANSACTIONS_TABLE=Inventory Transactions
```

## Render deployment

This repo includes `render.yaml` and is preconfigured for Airtable mode.

Add only:

- `AIRTABLE_PAT`
- `AIRTABLE_BASE_ID`

Render will then deploy the BOM-mapped version automatically.

## Files to review

- `airtable_import/bom_line_items_mapping.csv` - exact SKU-to-BOM mapping used in this build
- `airtable_import/parts_import.csv` - 43-item import file with all counts set to `0`

## Notes

- Blank `Quantity In Stock` values are treated as `0`.
- Whole-box kit labels are still disabled by default.


## Label size and print layout

The `/labels` page is laid out for **US Letter paper (8.5 x 11 in)** with each printed label sized to **30 mm tall x 90 mm wide** (3 cm x 9 cm). For best results, print with:

- **Scale:** 100% or Actual Size
- **Paper:** US Letter
- **Headers/footers:** Off

The printable labels are arranged in the same top-to-bottom order as the `BOM Line Items` CSV/PDF export.
