<!-- Copyright (c) 2024, AgriTheory and contributors
For license information, please see license.txt-->

# UOM Category Curation

<div class="byline">
  Tyler Matteson and Francisco Roldán 2026-08-14
</div>

ERPNext’s bundled setup fixtures contribute **239** packaged **UOM** masters plus **235** **UOM Conversion Factor** rows spread across **17** categories and certainly not all of them apply in all business contexts. Inventory Tools adds an **overview** panel and **UOM curation** actions on the **UOM Category** DocType to allow you to bulk enable or disable UOMs within that category.

## Where to find it

1. Open **UOM Category** (Stock module or Awesome Bar).
2. Save the category. The Inventory Tools overview section loads from a cached scan or starts a new **usage scan** automatically.
3. Use the **Actions** toolbar group **UOM curation** for **Refresh usage scan**, bulk disable, or bulk enable.

## Overview table

The table lists **one row per distinct UOM** that appears as **Conversion From UOM** or **Conversion To UOM** on any **UOM Conversion Factor** assigned to **this** category. If the category has no such factors yet, you see an empty-state message instead of a grid.

On large sites, building the overview scans every Link-to-UOM field on Item and submittable documents. That work runs as a **background job** with a **progress bar** on the form (similar to Check Run). Results are cached so reopening the category can show the last scan without re-running it; use **Refresh usage scan** to run again.

Columns:

| Column | Meaning |
|--------|---------|
| **UOM** | The UOM’s label (and document name if it differs). |
| **Is UOM Enabled?** | Whether the UOM master is enabled. |
| **Referenced in other UOM Categories** | **Yes** if this UOM also appears on any **UOM Conversion Factor whose category is not** the one you are viewing (including both from and to sides). Rows that only exist on *this* category’s factors alone do **not** count here. |
| **Transactional usage count** | Total number of Link-to-UOM references on **Item** or on **submittable** documents (header or child table line), counting **all** UOM link fields (`stock_uom`, `uom`, `weight_uom`, custom fields, etc.). Links on **UOM Conversion Factor** are **not** included. |

The short paragraph printed above the table on the form restates these rules for end users at the keyboard.

### Who can load the overview?

Overview and curation jobs require:

- ERPNext roles **Administrator**, or **System Manager**, **Stock Manager**, or **Item Manager**; and  
- Permission to write **UOM** (`UOM`: write).

If someone lacks access they get an insufficient-permission response.

## Disable unused UOMs and enable unused UOMs in this category

Both toolbar actions enqueue a background job that **re-scans usage**, then applies changes. Progress is shown on the form. All of these must stay true for a UOM to count as unused:

- It appears on at least one **UOM Conversion Factor** in **this category** (as from or to).  
- Its **transactional usage count** is **zero** (no Link references on Item or submittable document lines, across all UOM link fields).  
- It does **not** appear on **any UOM Conversion Factor** assigned to **another** category.

**Disable unused UOMs…** switches **enabled** unused masters **off**. Masters that already have **Enabled** unchecked are skipped.

**Enable all UOMs in this category** switches unused masters that are **currently disabled** back **on**. UOM names that remain in use elsewhere (transactional usage, other categories’ factors) never fall in the unused set, so neither action targets them.

Confirmation runs before either operation applies changes.
