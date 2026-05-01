<!-- Copyright (c) 2024, AgriTheory and contributors
For license information, please see license.txt-->

# UOM Category Curation

<div class="byline">
  Tyler Matteson 2026-05-01
</div>

ERPNext’s bundled setup fixtures contribute **239** packaged **UOM** masters plus **235** **UOM Conversion Factor** rows spread across **17** categories and certainly not all of them apply in all business contexts. Inventory Tools adds an **overview** panel and **UOM curation** actions on the **UOM Category** DocType to allow you to bulk enable or disable UOMs within that category.

## Where to find it

1. Open **UOM Category** (Stock module or Awesome Bar).
2. Save the category. The Inventory Tools overview section fills in after load.
3. Use the **Actions** toolbar group **UOM curation** for bulk disable / enable.

## Overview table

The table lists **one row per distinct UOM** that appears as **Conversion From UOM** or **Conversion To UOM** on any **UOM Conversion Factor** assigned to **this** category. If the category has no such factors yet, you see an empty-state message instead of a grid.

Columns:

| Column | Meaning |
|--------|---------|
| **UOM** | The UOM’s label (and document name if it differs). |
| **Is UOM Enabled?** | Whether the UOM master is enabled. |
| **Referenced in other UOM Categories** | **Yes** if this UOM also appears on any **UOM Conversion Factor whose category is not** the one you are viewing (including both from and to sides). Rows that only exist on *this* category’s factors alone do **not** count here. |
| **Referenced in Item or submitted documents** | **Yes** if a live value equals this UOM on an **Item** Link field, **or** on a **submittable** document: either the DocType header is submittable, **or** the field sits on a child table whose **parent** DocType is submittable. Links on **UOM Conversion Factor** are **not** included in this scan, so conversion-factor-only usage does **not** mark a UOM as “in use” for this flag. |

The short paragraph printed above the table on the form restates these rules for end users at the keyboard.

### Who can load the overview?

Overview and curation RPCs require:

- ERPNext roles **Administrator**, or **System Manager**, **Stock Manager**, or **Item Manager**; and  
- Permission to write **UOM** (`UOM`: write).

If someone lacks access they get an insufficient-permission response.

## Disable unused UOMs and enable unused UOMs in this category

Both toolbar actions depend on one shared notion of **unused** for **this category**. All of these must stay true for a UOM to count as unused:

- It appears on at least one **UOM Conversion Factor** in **this category** (as from or to).  
- It is **not** referenced on Item or submitted-document Link fields using the overview rules above.  
- It does **not** appear on **any UOM Conversion Factor** assigned to **another** category.

**Disable unused UOMs…** switches **enabled** unused masters **off**. Masters that already have **Enabled** unchecked are skipped.

**Enable all UOMs in this category** switches unused masters that are **currently disabled** back **on**. UOM names that remain in use elsewhere (Item, submissions, other categories’ factors) never fall in the unused set, so neither action targets them.

Confirmation runs before either operation applies changes.
