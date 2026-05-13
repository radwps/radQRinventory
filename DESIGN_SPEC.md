# RAD Box QR Inventory — Design Spec

## Overview

This document defines the visual design system, UX patterns, and proposed improvements for the RAD Box QR Inventory app. It is intended for use with Claude or a designer to produce updated templates and styles.

The app has two distinct usage contexts that must be designed for separately:
- **Desktop/admin** — dashboard, transaction log, labels page (used at a desk)
- **Mobile/scan** — scan pages triggered by QR code (used in the field, one-handed, often with gloves or in poor lighting)

---

## Current Design System

### Color tokens (defined in `styles.css`)

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#f6f8fb` | Page background |
| `--card` | `#ffffff` | Card/panel background |
| `--text` | `#1f2937` | Body text |
| `--muted` | `#6b7280` | Secondary/helper text |
| `--line` | `#d9e0ea` | Borders, dividers |
| `--accent` | `#1f6feb` | Primary CTA, links |
| `--danger` | `#b42318` | Destructive actions (Subtract), errors |
| `--success` | `#0f766e` | Success states |
| `--secondary` | `#475467` | Secondary buttons |
| `--site-header-bg` | Set by `APP_VARIANT` | Dark navy (live) or orange (QA) |

### Typography

- **Font:** Arial, Helvetica, sans-serif (system font stack)
- **Base size:** browser default (~16px)
- No type scale currently defined — headings use browser defaults

### Layout

- Max content width: `1120px`, centered, `2rem` side padding on mobile
- Cards: white, `14px` border-radius, subtle shadow, `1px` border
- Forms: grid-based with `0.9rem` gaps; inputs have `10px` radius

### Components

- **Pill/Button:** Rounded (`999px`), accent-colored, `0.6rem 0.9rem` padding
- **Table:** Full-width, left-aligned, bottom borders on rows
- **Alert/Error:** Rounded box, color-coded background + border
- **Mode toggle:** Custom CSS checkbox toggle (standard vs. receive mode)
- **Scan choice buttons:** 2-column grid, large tap targets (`0.9rem 1rem` padding)

---

## Proposed Improvements

### 1. Type scale

The current design relies on browser default heading sizes. Define an explicit scale:

```
--text-xs:   0.75rem   (11px) — label copy, fine print
--text-sm:   0.875rem  (14px) — table cells, helper text
--text-base: 1rem      (16px) — body
--text-lg:   1.125rem  (18px) — card headings, subheadings
--text-xl:   1.375rem  (22px) — page headings (h2)
--text-2xl:  1.75rem   (28px) — hero/app title
```

Apply `font-size: var(--text-xl)` to `h2`, `var(--text-lg)` to `h3`, etc.

---

### 2. Mobile scan page — major UX improvement

The scan page (`scan_part.html`) is the most-used screen. It opens directly from a QR scan on a phone in a physical environment. Current pain points and fixes:

**Part name is hard to read quickly**
- Current: part name is in an `<h2>` with no visual emphasis on what matters
- Proposed: add a large, bold part name at the top of the card, with the on-hand count shown prominently as a badge

```
┌────────────────────────────────┐
│  MP3 Player                    │
│  SKU: RAD-MP3-PLAYER           │
│  On hand: [  47  ]  ← large badge│
└────────────────────────────────┘
```

**Action buttons need to be bigger on mobile**
- Current: `0.9rem 1rem` padding, side by side
- Proposed: minimum `56px` height (`min-height: 3.5rem`), full width stacked on screens below `480px`, with stronger visual differentiation between Add (accent blue) and Subtract (danger red)

**Confirmation step before submitting**
- Currently a scan submit is instant and irreversible
- Proposed: on mobile, after pressing Add or Subtract, show an inline "Confirm [Add / Subtract] [qty]?" state before the form actually submits. This prevents accidental taps.

```
[Add inventory] → [Confirm: Add 1 to MP3 Player?] [Yes] [Cancel]
```

**On-hand count visibility after scan**
- The success page shows the updated count, which is good
- Proposed: on the success page, show the delta as a large visual indicator (e.g. "+1" in green or "−3" in red) before the table

---

### 3. Dashboard improvements

**Low-stock highlighting**
- Current: low-stock rows get a `#fff5f5` background — subtle, easy to miss
- Proposed: add a colored left border accent (`border-left: 3px solid var(--danger)`) and a small "Low" badge in the On Hand cell

**On-hand count column**
- Current: plain number
- Proposed: color-code the number — red if at/below reorder level, amber if within 20% above reorder level, default text otherwise

**Recent transactions**
- Current: 9-column table, dense, includes Batch ID and Delta which are low-signal to most users
- Proposed: hide Batch ID and Delta by default; collapse them behind a "Show details" disclosure or reduce to smaller text. Prioritize: Time, Part, Action, Qty, Operator.

**Action column on parts table**
- Current: "Open scan page" pill — unclear what it does
- Proposed: label it "Scan / Update" and add two small quick-action links: "Add" and "Subtract" directly in the row so desktop admin users can act without scanning

---

### 4. Visual hierarchy — header

The site header is functional but flat. Suggested refinements:
- Add a small RAD logo/wordmark slot (even a placeholder text mark) to the left of the title
- Reduce the subtitle text size to `var(--text-sm)` and use `opacity: 0.75` instead of the `--muted` token (which is dark text, not white-muted)
- On mobile, stack the nav links below the title with `gap: 0.5rem` and smaller font

---

### 5. Status / health indicator in header

The `/health` endpoint exists but is just a nav link. Proposed:
- Show a small dot indicator in the header nav next to "Health": green dot if Airtable is reachable, red if not
- Fetched via a lightweight `<span>` element that does a background fetch to `/health` on page load
- Degrades gracefully (no dot shown if fetch fails)

---

### 6. Labels page improvements

The printable label page is strong. Small additions:

**On-screen preview**
- Add a brief instruction card above the label pages explaining print settings (scale: 100%, no headers/footers) — currently this lives only in the README

**Label card content**
- Current: QR code + part name + SKU code
- Proposed: add a small line for `container_label` if set, so the printed label shows where the bin lives (e.g. "Shelf B-3")

**Whole RAD Box label**
- Current: large 56mm QR with orange border
- Proposed: add "Whole RAD Box Unit" as a bold title line above the QR, and the action reminder ("Scan to add/subtract all parts") as a small subtitle below — so the label is self-describing without the app open

---

### 7. Color / accessibility

**Contrast**
- `--muted` (`#6b7280`) on `--bg` (`#f6f8fb`) is ~4.0:1 — passes AA for normal text but borderline
- Darken `--muted` to `#555f6e` for better compliance without changing the visual feel

**Focus states**
- Currently no visible `focus-visible` styles on buttons or inputs — add:
  ```css
  :focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  ```

**Touch target minimums**
- All interactive elements should meet 44×44px minimum. Audit: the nav links in the header are currently text-sized and likely fall below this on mobile.

---

### 8. Empty states

**No transactions yet** — currently renders an empty table with headers. Show a placeholder message instead:
> "No transactions recorded yet. Scans will appear here."

**Whole RAD Box Unit not configured** — currently a `<p class="subtle">` line. Make this more visually distinct — a small callout box with instructions on how to configure it (fill in Parts per RAD Unit in Airtable).

---

### 9. Toast / feedback on success

Currently the success state is a full-page redirect. This is fine for mobile (QR scans). For desktop use, consider:
- A lightweight inline success banner at the top of the scan page after submission, with the updated count, instead of navigating away
- Back button behavior: after success, "Return to dashboard" should use `history.back()` or the referring URL, so the user doesn't have to re-navigate deep into the dashboard

---

## Page-by-page summary

| Page | Current state | Priority improvements |
|---|---|---|
| Dashboard | Functional, clean | Low-stock badges, quick-action links in row, transaction column cleanup |
| Scan part | Good toggle UX | Bigger tap targets, confirm step, larger part name/count display |
| Scan whole unit | Basic | Same tap target improvements as scan part |
| Scan kit | Minimal | Same improvements; kit component summary would help |
| Success | Works | Delta badge ("+1" / "−3"), smarter back navigation |
| Labels | Strong | Print instruction card, container label line, Whole Unit label copy |
| Health | Just a JSON page | Inline status dot in header nav |

---

## Implementation notes for Claude

- All styles live in `app/static/styles.css` (single file, no build step)
- Templates are Jinja2 in `app/templates/`; `base.html` is the shell
- Inline `<style>` blocks inside templates are acceptable for page-specific styles (already used in `scan_part.html`)
- Inline `<script>` is acceptable; no bundler or npm involved
- Do not introduce external CSS frameworks or JS libraries — keep it zero-dependency on the frontend
- Print layout for labels is critical — test any label changes at `@media print`
- The `--site-header-bg` variable is set inline in `base.html` from the server; do not hardcode it
