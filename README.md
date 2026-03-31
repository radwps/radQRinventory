# RAD Box QR Inventory Prototype

This build is configured for the existing Airtable base **RAD Operations Tracker (LIVE)** using the **BOM Line Items** table structure you exported to CSV.

## What this build now does

- Uses **BOM Line Items** as the Airtable inventory source table.
- Reads the part name from **Line Item Name**.
- Reads and writes inventory counts directly to **Quantity In Stock**.
- Filters Airtable down to the 12 QR-coded RAD parts only.
- Uses one QR code per part container.
- Keeps the mock/demo mode intact for offline testing.

## BOM field mapping used by this build

- Table: `BOM Line Items`
- Part name field: `Line Item Name`
- Count field: `Quantity In Stock`
- QR/scan identifiers: the app uses stable internal SKUs such as `RAD-MP3-PLAYER`, mapped to the matching BOM line item.

## Important behavior change from the earlier Airtable version

Earlier versions expected a separate Airtable **Parts** table plus a **Transactions** table and let Airtable formulas compute on-hand counts.

This version is different:

- it updates **Quantity In Stock** on the matching **BOM Line Items** record directly
- transaction logging is **optional** and off by default

That makes the app work with the CSV structure you provided, even if you do not yet have a separate inventory transactions table in Airtable.

## The 12 BOM items this build looks for

The app maps these display names to the corresponding exported BOM line items, including the name variants found in your CSV:

- MP3 Player
- 8 GB SD Card → matches `8 GB SD Card (for MP3)`
- HiLetgo PAM8610 Mini Stereo AMP
- Potentiometer Control Knobs for Amp → matches `30 PCS 6mm Potentiometer Control Knobs for Amp`
- 12V to 5V Converter USB-C → matches `12v to 5v Converter USB-C`
- 1x12 Position Power Distribution Board → matches `1X 12 Position Power Distribution Board`
- DC Barrel Glands
- CNLINKO USB-C Gland
- CNLINKO LP12 4-Pin Circular Connector with 1 Meter Cable
- Audio Gland
- 6" Audio Jump Cable Amp & Out → matches `6" audio jump cable Amp & Out`
- 12V 5A DC Power Pigtail Cord Male Plug Connectors → matches `20-Pack 12V 5A DC Power Pigtail Cord Male Plug Connectors, 5.5mm x 2.1mm`

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

In this build, the rest of the Airtable mapping defaults already point at the BOM structure from your CSV.

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

## Notes

- Blank `Quantity In Stock` values are treated as `0`.
- Whole-box kit labels are still disabled by default.
- The file `airtable_import/bom_line_items_mapping.csv` shows the exact app-to-BOM name mapping used in this build.
