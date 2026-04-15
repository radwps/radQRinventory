# QA Version of RAD Box QR Inventory Prototype

This build is configured for the current Airtable base **RAD Operations Tracker (LIVE)** using the **Inventory** table you exported.

## What this update fixes

- Uses **Inventory** as the default Airtable inventory source table.
- Falls back automatically between **Inventory** and **BOM Line Items** so an old environment variable does not break the app.
- Reads the part name from **Line Item Name**.
- Reads and writes inventory counts directly to **Quantity In Stock**.
- Filters Airtable to the **43 nonblank inventory line items** found in your export.
- Loads the part catalog and the website display order directly from `airtable_import/inventory_mapping.csv` at runtime.
- If you change the row order in that CSV, the dashboard and printable labels follow the new order after redeploy/restart.
- Preserves the same internal SKUs and QR routes for previously existing items.
- Keeps printable labels at **90 mm wide x 30 mm tall** on **US Letter** paper.

## Inventory field mapping used by this build

- Table: `Inventory` (with automatic fallback to `BOM Line Items`)
- Part name field: `Line Item Name`
- Count field: `Quantity In Stock`
- Optional extra field present in your export: `Ordered`
- QR/scan identifiers: stable internal SKUs such as `RAD-MP3-PLAYER`, mapped to the matching inventory line item

## Name changes handled in this update

The app now accepts the updated Airtable names for these existing SKUs:

- `RAD-IP67-JBOX` -> `IP67 Waterproof Junction Box (11.8x7.9x6.3)`
- `RAD-CWT5015-RTU` -> `4G RTU Remote Terminal Unit CWT5015`
- `RAD-AMP-HOUSING-3D` -> `3d Housing for Amp (Filament)`

Older matching names are still accepted too.

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

If you want the setting to be explicit, also set:

```env
AIRTABLE_PARTS_TABLE=Inventory
```

## Render deployment

This repo includes `render.yaml` configured for the `Inventory` table.

After deploying, add only:

- `AIRTABLE_PAT`
- `AIRTABLE_BASE_ID`

If your existing Render service already has `AIRTABLE_PARTS_TABLE=BOM Line Items`, this code now auto-falls back and should still work after redeploy. You can still update the Render environment variable to `Inventory` to make the configuration clearer.

## Files to review

- `airtable_import/inventory_mapping.csv` - exact SKU-to-Inventory mapping used in this build **and the display order source for the website**
- `airtable_import/parts_import.csv` - 43-item import file with all counts set to `0`

## Notes

- Blank `Quantity In Stock` values are treated as `0`.
- Blank line-item rows in Airtable are ignored.
- Whole-box kit labels are still disabled by default.

## Label size and print layout

The `/labels` page is laid out for **US Letter paper (8.5 x 11 in)** with each printed label sized to **30 mm tall x 90 mm wide** (3 cm x 9 cm). For best results, print with:

- **Scale:** 100% or Actual Size
- **Paper:** US Letter
- **Headers/footers:** Off
