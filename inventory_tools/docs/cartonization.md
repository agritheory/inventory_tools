<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Cartonization Configuration & Validation Guide

## 1. Purpose of Cartonization

Cartonization ensures that items involved in inventory transactions
(Pick List, Stock Entry, Delivery Note, etc.) physically fit into their
target containers (warehouses, bins, pallets, cartons).

It validates packing feasibility using:
- Physical dimensions of items
- Physical dimensions of containers
- Configurable packing algorithms
- Configurable enforcement policies

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
| Allow Rotation | Allows item rotation in solver |
| Solver Timeout (Seconds) | Maximum time allowed for 3D fitted solver |
| Weight Validation | Ignore / Warn / Error for weight limits |
| Max Weight UOM | Unit used for weight comparison |

---

### 2.5 Applicable Document Types

Cartonization runs only for selected document types defined in
**Cartonization Doctypes**.

Examples:
- Pick List
- Stock Entry
- Delivery Note

---

## 3. Physical Dimension Doctype Integration

### 3.1 Item Physical Dimensions (Exterior)

Attached to Item records.

Represents the space the item occupies.

Required fields:
- Length
- Width
- Height
- Weight
- UOM

Quantity handling:
```
Effective volume = item volume × quantity
```

---

### 3.2 Container Physical Dimensions (Interior)

Attached to Warehouse or container-type Items.

Represents the available space inside the container.

Required fields:
- Interior Length
- Interior Width
- Interior Height
- Max Weight

---

### 3.3 Warehouse-Level Exemption

Warehouse may be marked as cartonization exempt.
If enabled, validation is skipped.

---

## 4. Packing Algorithms Explained

### 4.1 2D Floor Packing

Checks only footprint area.

```
Total footprint ≤ container floor area
```

Ignores height and stacking.

---

### 4.2 3D Volumetric Packing

Checks total volume only.

```
Total volume ≤ container volume
```

Ignores geometry and placement.

---

### 4.3 3D Fitted Packing

Uses a 3D bin-packing solver (python-mip).

Considers:
- Exact dimensions
- Quantity
- Orientation (if allowed)

Possible solver results:
- OPTIMAL
- FEASIBLE
- INFEASIBLE
- OTHER (timeout / undecided)

---

## 5. Quantity Handling

Item quantity is always considered.

Each unit is treated as a separate box in 3D fitted mode.

---

## 6. Policy Behavior

### Ignore
- Validation skipped

### Warn
- Validation runs
- Warning shown
- Document proceeds

### Error
- Validation runs
- Failure blocks submission

---

## 7. Execution Flow

```
Document Save / Submit
  → Check Cartonization Enabled
  → Check Document Type
  → Resolve Warehouse
  → Fetch Dimensions
  → Run Packing Algorithm
  → Apply Policy
```

---

## 8. Recommended Configuration

| Scenario | Recommendation |
|--------|----------------|
| High volume picking | 3D Volumetric + Warn |
| Precise shipping | 3D Fitted + Error |
| Pallet operations | 2D Floor + Warn |
| Initial rollout | Warn policies |

---

## 9. Summary

Cartonization provides a configurable mechanism to ensure
inventory movements are physically feasible by validating
dimensions, quantities, and container limits.