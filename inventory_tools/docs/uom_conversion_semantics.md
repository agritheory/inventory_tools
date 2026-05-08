<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# UOM conversion semantics (Inventory Tools)

## Purpose

ERPNext **[UOM Conversion Factor](https://docs.erpnext.com/)** requires a numeric **Value**. Some real-world ratios (for example pallet vs weight) are intentionally **not** a single global constant. Inventory Tools adds **Conversion basis (Inventory Tools)** (`it_conversion_basis`) on **UOM Conversion Factor**:

| Value stored | Meaning for strict tooling |
| --- | --- |
| unset / empty | Same as **fixed** (backward compatible default). |
| **fixed** | Row participates in naive fixed-ratio / ambiguity suspicion. |
| **contextual** | Row is intentionally non-universal; suspicion reports should **skip** naive 1:1 / fixed-ratio checks for this row or show an informational “marked variable” state. |

## What this does **not** change

- **`get_uom_conv_factor`** and core stock qty resolution continue to use the numeric **Value** when a row matches. **`contextual` is metadata for Inventory Tools tooling**, not a change to ERPNext resolver behavior.
- For item-specific ratios, rely on **[Item UOM Conversion Detail](https://docs.erpnext.com/)** and transaction-level UOMs as ERPNext intends.

## Python helpers

Module `inventory_tools.inventory_tools.uom_conversion_semantics` (`inventory_tools/inventory_tools/uom_conversion_semantics.py`) exposes:

- `is_contextual_conversion_factor(doc)` — carve-out predicate.
- `participates_in_strict_conversion_checks(doc)` — inverse for validators.
- `qb_uom_conversion_factor_strict_rows(ucf)` / `qb_uom_conversion_factor_contextual_rows(ucf)` — Query Builder filters for reports.

## UX copy (future reports)

When listing excluded contextual rows, prefer short notes such as: **“Marked contextual — global factor not validated”** or **“Intentionally variable (per item/shipment); not checked for fixed ratio.”**
