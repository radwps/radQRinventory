# RAD Box QR Inventory — Project Context

## What this system does

This is a web app for tracking physical inventory of RAD Box parts. Team members scan a QR code on a storage bin, which opens a form on their phone to add or subtract parts. All counts sync live to Airtable. The `/labels` page generates printable QR labels (90mm × 30mm, 16 per page on US Letter) for each part.

## Technology

- **Backend:** Python 3, FastAPI, Uvicorn
- **Templates:** Jinja2 HTML (no frontend framework)
- **Data store:** Airtable (live) or SQLite mock (local dev)
- **Deployment:** Render (configured via `render.yaml`); Dockerized

## How the data flows

```
QR label scan → /scan/part/{sku}?action=add|subtract
                        ↓
              AirtableStore.apply_part_action()
                        ↓
         PATCH Airtable "Inventory" table (Quantity In Stock field)
                        ↓ (optional)
         POST Airtable "Inventory Transactions" table (audit log)
```

The app reads and writes directly to Airtable on every request — there is no local database in production.

## Key concepts

### SKUs
Every part has an internal SKU like `RAD-MP3-PLAYER`. These are stable identifiers used in QR URLs. They are mapped to Airtable row names (e.g. "MP3 Player") via `airtable_import/inventory_mapping.csv`. If Airtable renames a part, add the new name as an alias in that CSV — do not change the SKU.

### Part catalog
`app/part_catalog.py` holds the master SKU list and controls dashboard/label display order. It loads from `airtable_import/inventory_mapping.csv` at startup. To add a new part or change display order, edit that CSV and redeploy.

### Store modes
Controlled by the `STORE_MODE` env var:
- `mock` (default for local dev) — reads/writes a local SQLite file at `demo_data/radbox_inventory.db`
- `airtable` — reads/writes the live Airtable base; requires `AIRTABLE_PAT` and `AIRTABLE_BASE_ID`

### Actions
Parts support four actions: `add`, `subtract`, `receive`, `undo_receive`. Receive/undo_receive are purchase-order workflows that require selecting a PO from Airtable. Add/subtract are simple count changes.

### Whole RAD Box Unit
A virtual "kit" assembled from all parts that have a nonzero `Parts per RAD Unit` value in Airtable. Scanning its QR code adds or subtracts all component quantities at once. Configured entirely in Airtable — no code change needed.

### Kits (disabled by default)
Multi-part kits defined in Airtable `Kits` and `Kit Items` tables. Enable with `ENABLE_KITS=true`. Not currently in use for RAD Box production.

### QA vs Live variants
Set `APP_VARIANT=qa` to switch the header to orange with a "QA Version" prefix. Useful for running a staging instance pointed at a test Airtable base.

## Airtable tables used

| Table | Purpose |
|---|---|
| `Inventory` | One row per part; `Quantity In Stock` is the live count |
| `Inventory Transactions` | Audit log of every scan (optional; off by default) |
| `Purchase Orders` | PO list for receive workflow |
| `Kits` | Kit definitions (only if `ENABLE_KITS=true`) |
| `Kit Items` | Kit BOM (only if `ENABLE_KITS=true`) |

The app auto-falls back from `Inventory` to `BOM Line Items` if the configured table isn't found — this is intentional for backward compatibility with older Airtable base setups.

## Important files

| File | What it does |
|---|---|
| `app/main.py` | All FastAPI routes and request handling |
| `app/store.py` | Abstract `InventoryStore` interface and data models (`Part`, `Transaction`, `Kit`) |
| `app/airtable_store.py` | Airtable implementation of `InventoryStore` |
| `app/mock_store.py` | SQLite implementation for local dev |
| `app/config.py` | All settings via env vars; SKU prefix helpers |
| `app/part_catalog.py` | Master part list, name normalization, catalog sort order |
| `airtable_import/inventory_mapping.csv` | SKU↔Airtable name mapping; controls display order |
| `.env.example` | Template for all environment variables |
| `render.yaml` | Render deployment config |
| `Dockerfile` | Container build |

## Local development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with mock data (no Airtable needed)
python -m uvicorn app.main:app --reload

# Run against live Airtable
cp .env.example .env
# Edit .env: set STORE_MODE=airtable, AIRTABLE_PAT, AIRTABLE_BASE_ID
python -m uvicorn app.main:app --reload
```

Visit `http://localhost:8000` for the dashboard, `http://localhost:8000/labels` for printable labels.

## Deployment (Render)

The repo includes `render.yaml`. After connecting the repo in Render, set only two environment variables:
- `AIRTABLE_PAT` — your Airtable personal access token
- `AIRTABLE_BASE_ID` — the base ID (starts with `app`)

Everything else has working defaults. Redeploy after any CSV or code change.

## Adding or renaming a part

1. Add (or update) the row in `airtable_import/inventory_mapping.csv` — columns: `App SKU`, `App Display Name`, `Inventory Name Used`, `Accepted Alternate Match`
2. The new SKU will appear in the dashboard and labels after the next restart/redeploy
3. The Airtable row name must match `Inventory Name Used` exactly (or be listed as an alternate match)
4. Print a new label from `/labels` and attach it to the bin

## Constraints to know

- **No negative stock by default.** Subtracting below zero is blocked unless `ALLOW_NEGATIVE_STOCK=true`.
- **No authentication.** The app is URL-accessible; security relies on the Render URL being kept internal or behind a VPN/password.
- **Airtable rate limits.** Each page load re-fetches from Airtable. Under normal scan usage this is fine; bulk operations may hit the 5 req/sec limit.
- **SKUs are permanent.** QR labels encode the SKU in the URL. Renaming a SKU means reprinting labels and updating the CSV.
