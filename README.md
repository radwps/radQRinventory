# RAD Box QR Inventory Prototype

This is a lightweight mobile-friendly web app for RAD Box inventory.

## What is included in this version

- One QR code per part container.
- The scan page lets the operator choose **Add inventory** or **Subtract inventory**.
- A running transaction log.
- Mobile-friendly pages for phone scanning.
- A Render-ready deployment config for a free public URL.
- A Dockerfile for other container-based hosts.
- A revised demo catalog with these 12 starting parts, all at zero count:
  - MP3 Player
  - 8 GB SD Card
  - HiLetgo PAM8610 Mini Stereo AMP
  - Potentiometer Control Knobs for Amp
  - 12V to 5V Converter USB-C
  - 1x12 Position Power Distribution Board
  - DC Barrel Glands
  - CNLINKO USB-C Gland
  - CNLINKO LP12 4-Pin Circular Connector with 1 Meter Cable
  - Audio Gland
  - 6" Audio Jump Cable Amp & Out
  - 12V 5A DC Power Pigtail Cord Male Plug Connectors

Kit-level whole-box QR codes are disabled by default in this build.

## Files added for deployment

- `render.yaml` for Render
- `Dockerfile` and `.dockerignore` for other container-based hosts
- `airtable_import/parts_import.csv` to import the 12 parts into Airtable

## Recommended production architecture

Use Airtable as the system of record and keep the web app stateless.
The app should write transaction records, and Airtable should calculate current stock.
That avoids data loss on free hosts that do not provide persistent local storage.

### Airtable tables

#### 1) Parts
Suggested fields:

- `SKU` (single line text, unique)
- `Part Name` (single line text)
- `Container Label` (single line text)
- `Starting Qty` (number)
- `Reorder Level` (number)
- `Transactions` (linked records to Transactions)
- `Qty Delta Rollup` (rollup of `Transactions -> Delta`, with `SUM(values)`)
- `On Hand` (formula: `VALUE({Starting Qty}) + VALUE({Qty Delta Rollup})`)

#### 2) Transactions
Suggested fields:

- `Part` (linked record to Parts)
- `SKU` (single line text)
- `Action` (single select or text)
- `Quantity` (number)
- `Delta` (number; positive for add, negative for subtract)
- `Batch ID` (single line text)
- `Operator` (single line text)
- `Note` (long text)
- `Source` (single line text)
- `Scanned At` (date/time)

## Local test run

From the project folder:

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Then open:

```text
http://localhost:8000
```

If you update the seed list and want the mock database to match it again, either click **Reset demo data** on the dashboard or delete `demo_data/radbox_inventory.db` and restart.

## Switching to Airtable mode locally

1. Copy `.env.example` to `.env`.
2. Set:
   - `STORE_MODE=airtable`
   - `AIRTABLE_PAT=...`
   - `AIRTABLE_BASE_ID=...`
3. Import `airtable_import/parts_import.csv` into your Airtable **Parts** table if you want the 12 default items preloaded.
4. Start the app.

Example:

```bash
python -m uvicorn app.main:app --reload
```

This project now loads a local `.env` file automatically if it exists.

## Render deployment

This repo includes `render.yaml`, so Render can create the service from the repository.

### Fastest path

1. Put this project in a GitHub repository.
2. In Render, choose **New +** then **Blueprint**.
3. Select the repository.
4. During setup, enter values for:
   - `AIRTABLE_PAT`
   - `AIRTABLE_BASE_ID`
5. Deploy.

The included `render.yaml` uses:

- a **free** web service
- `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`
- `/health` as the health check path
- `STORE_MODE=airtable`
- `ENABLE_KITS=false`

Once deployed, Render gives the app a public URL. The labels page will use that host automatically when `PUBLIC_BASE_URL` is not manually set.

## Other hosting options

Because a `Dockerfile` is included, the app can also be deployed on container-friendly hosts such as Koyeb or any VPS/container platform. If you deploy somewhere other than Render, make sure the host sets a stable public URL and that your environment variables are configured.

## QR workflow

Each printed part QR stores a URL such as:

```text
https://your-app.example.com/scan/part/RAD-MP3-PLAYER
https://your-app.example.com/scan/part/RAD-PAM8610-AMP
```

The phone opens a simple page that shows the part, current on-hand quantity, quantity field, operator initials, and note field. The user then taps either **Add inventory** or **Subtract inventory**.

## Notes

- The demo data now includes only the 12 items listed above.
- In Airtable mode, the app expects the `On Hand` value to be calculated by Airtable formulas and rollups.
- For production, use Airtable mode instead of hosted mock mode.
- Kit support can be re-enabled later by setting `ENABLE_KITS=true` and filling out kit tables.

## Tests

Run:

```bash
pytest
```
