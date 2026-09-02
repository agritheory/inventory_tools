<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Cartonization Configuration & Validation Guide

<div class="byline">
  IshwaryaM1030, Tyler Matteson, and Francisco Roldán 2026-08-24
</div>


## 1. Purpose of Cartonization

Cartonization ensures that items involved in inventory transactions
(Pick List, Stock Entry, Delivery Note, etc.) physically fit into their
target containers (warehouses, bins, pallets, cartons).

It validates packing feasibility using:
- Physical dimensions of items
- Physical dimensions of containers
- Configurable packing algorithms
- Configurable enforcement policies

Validation runs on document **submission**, not on save. Documents can
be saved freely; cartonization is only enforced at submit time.

---

## 2. Inventory Tools Settings – Cartonization Configuration

Cartonization is configured from:

**Inventory Tools Settings → Cartonization Tab**

### 2.1 Enable / Disable

| Field | Description |
|-----|------------|
| Enable Cartonization | Master switch. If unchecked, all cartonization logic is skipped |

---

### 2.2 Packing Mode Configuration

| Field | Description |
|-----|------------|
| Default Packing Mode | Algorithm used to validate packing |

Available modes:
- 2D Floor Packing
- 3D Volumetric
- 3D Fitted

---

### 2.3 Validation Policies

Each packing mode has an independent policy:

| Policy | Behavior |
|------|---------|
| Ignore | Validation is skipped |
| Warn | Validation runs, warning is shown, document proceeds |
| Error | Validation runs, document submission is blocked |

Configured fields:
- Floor Packing Policy
- Volumetric Policy
- Fitted Policy

---

### 2.4 Additional Options

| Field | Description |
|-----|------------|
| Allow Rotation | Allows item L/W rotation in the 3D fitted solver |
| Solver Timeout (Seconds) | Maximum time allowed for 3D fitted solver (default: 30) |
| Weight Validation | Ignore / Warn / Error for weight limit checks |
| Max Weight UOM | Unit used for weight comparison (informational) |

---

### 2.5 Applicable Document Types

Cartonization runs only for document types listed in
**Cartonization Doctypes**. Only documents whose doctype appears in
this list are validated.

Examples:
- Pick List
- Stock Entry
- Delivery Note

---

## 3. Physical Dimension Doctype Integration

Physical dimensions are stored in the **Physical Dimension** doctype.
To set up dimensions for an item or warehouse, create a Physical
Dimension record with:

- **Reference Doctype**: `Item` or `Warehouse`
- **Reference Document**: the Item or Warehouse name
- **Dimension Type**: `Exterior` for items, `Interior` for containers
- **Item UOM** (`Item` references only): which handling unit the exterior dimensions describe
- **UOM**: the unit for length / width / height numeric values (e.g., `Meter`)
- Length, Width, Height, Weight fields as described below

Volume is computed automatically from Length × Width × Height on save.

### 3.1 Item Physical Dimensions (Exterior)

Attached to Item records.

Represents the space the item occupies **per unit of handling UOM** (see **Item UOM** below).

Required fields:
- Length
- Width
- Height
- Weight (weight per unit **in this Item UOM**)
- **Item UOM** (mandatory): the stocking / handling unit these dimensions describe (for example stock UOM **Pound** vs alternate **Box**). Must be either the Item’s stock UOM or an alternate UOM defined on **UOM Conversion Detail** rows for that Item.
- UOM (dimensional unit for L/W/H numeric fields, e.g., `Meter`)

You may maintain **multiple** Exterior Physical Dimensions for one Item — for example **Pound-level** dims and **Box-level** dims. Document names default to **`{Item}-{Interior|Exterior}-{dimensional UOM}-{Item UOM}`** for Items, and **`{Reference}-{Interior|Exterior}-{dimensional UOM}`** for Warehouses.

Quantity handling:

Cartonization converts each transaction line **first to quantity in Stock UOM** (using `picked_qty`, `stock_qty`, or `transfer_qty` when ERPNext exposes them on the row, otherwise `qty` × conversion from line UOM to Stock UOM), **then divides by the Conversion Detail factor for the resolved Physical Dimension’s Item UOM** to get how many rigid units to validate.

Effective counts use the Exterior row whose **Item UOM** matches the line’s **transaction UOM** when possible; otherwise the row whose **Item UOM** equals the Item’s Stock UOM, otherwise the alphabetically earliest matching Exterior row:

```
effective_unit_count =
    qty_stock_uom / conversion_factor(one unit of pd_row.item_uom, expressed in stock_uom)

Effective floor area = item length × item width × effective_unit_count
Effective volume     = item volume × effective_unit_count
Effective weight     = item weight × effective_unit_count
```

---

### 3.2 Container Physical Dimensions (Interior)

Attached to Warehouse or container-type Items.

Represents the available space inside the container.

Required fields:
- Interior Length
- Interior Width
- Interior Height
- Weight (used as **max weight capacity** for weight validation)
- UOM (must match item dimensions UOM for meaningful comparison)

---

### 3.3 Warehouse-Level Exemption

A Warehouse may be marked **Cartonization Exempt** via the
`cartonization_exempt` checkbox on the Warehouse form.
If enabled, all cartonization validation is skipped for that warehouse.

---

## 4. Packing Algorithms Explained

### 4.1 2D Floor Packing

Checks only footprint area.

```
Total footprint ≤ container floor area
```

Ignores height and stacking. Suitable for pallet operations.

---

### 4.2 3D Volumetric Packing

Checks total volume only.

```
Total volume ≤ container volume
```

Ignores geometry and placement. Fast and conservative.

---

### 4.3 3D Fitted Packing

Uses a 3D bin-packing MIP solver (python-mip / CBC).

Each item unit is treated as a separate box. The solver assigns
a position (x, y, z) to each box and enforces:
- All boxes remain within container bounds
- No two boxes overlap (disjunctive big-M constraints)
- Optional L/W rotation when Allow Rotation is enabled

Possible solver results:
- OPTIMAL — all items placed without overlap
- FEASIBLE — a valid placement was found within the time limit
- INFEASIBLE — no valid placement exists
- OTHER — solver timed out without a conclusive result

---

## 5. Weight Validation

Weight validation is independent of the packing mode. The total weight
of all items going to a warehouse is compared against the `Weight`
field on the warehouse's Interior Physical Dimension.

If no max weight is set on the container (Weight = 0), weight
validation is always passed.

Weight policy is configured separately from the dimensional policy
in the **Weight Validation** field.

---

## 6. Quantity Handling

Item quantity is always considered.

- 2D Floor: area scaled by qty
- 3D Volumetric: volume scaled by qty
- 3D Fitted: each unit is a separate box in the solver
- Weight: weight scaled by qty

---

## 7. Policy Behavior

### Ignore
- Validation skipped

### Warn
- Validation runs
- Warning shown in the UI
- Document proceeds to submit

### Error
- Validation runs
- Failure blocks submission with a validation error

---

## 8. Execution Flow

```
Document Submit
  → Check Cartonization Enabled (Inventory Tools Settings)
  → Check Document Type is in Cartonization Doctypes
  → For each item row, resolve Warehouse
  → Fetch Item Physical Dimensions (Exterior)
  → Group items by Warehouse
  → For each Warehouse:
      → Check cartonization_exempt flag
      → Fetch Warehouse Physical Dimensions (Interior)
      → Run configured Packing Algorithm
      → Apply Dimensional Policy
      → Run Weight Validation
      → Apply Weight Policy
```

---

## 9. Recommended Configuration

| Scenario | Recommendation |
|--------|----------------|
| High volume picking | 3D Volumetric + Warn |
| Precise shipping | 3D Fitted + Error |
| Pallet operations | 2D Floor + Warn |
| Initial rollout | Warn policies for all modes |

---

## 10. Summary

Cartonization provides a configurable mechanism to ensure
inventory movements are physically feasible by validating
dimensions, quantities, weight, and container limits.
All policies (Ignore / Warn / Error) are independently configurable
per packing mode so teams can tune enforcement to their workflow.
