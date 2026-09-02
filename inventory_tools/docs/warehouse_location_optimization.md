<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Warehouse Location Optimization

<div class="byline">
  Tyler Matteson 2026-08-23
</div>


Inbound path-based optimization takes a "set and periodically correct course" approach in Inventory Tools. Warehouse Location Optimization is a report that ranks items by how often they move in the area defined within a Warehouse Plan, then suggests storage locations for putaway. The goal is to place hotter items nearer the plan pickup point so receiving and replenishment walks stay short.

The report works with a [Warehouse Plan](./warehouse_plan.md): candidate bins must sit on that plan (when required in settings), and walk distance uses the plan pickup point and bin access paths.

From the report you can:

- Set each item’s **default warehouse** for the company to the suggested location
- Create or update an ERPNext **Putaway Rule** for the suggested location, using **Slot Capacity** from physical dimensions

In scenarios where the company operates more than one physical warehouse, Putaway Rule is recommended. 

## Prerequisites

1. A **Warehouse Plan** with pickup point and warehouses placed on the plan (coordinates / accessible path). See [Warehouse Plan](./warehouse_plan.md).
2. **Stock Ledger** activity in the date range you care about (receipts, transfers, deliveries, and so on) for warehouses in scope.
3. For reliable fit and capacity: **Physical Dimension** records — item **Exterior** and warehouse **Interior** (same dimension model used by [Cartonization](./cartonization.md)).

Without dimensions, Fit Status is `unverified` and Slot Capacity is blank; **Create Putaway Rule** will not run for those rows until dimensions exist.

## Running the report

Open **Warehouse Location Optimization** (Script Report) and set:

| Filter | Purpose |
|--------|---------|
| Company | Company whose stock and warehouses are in scope |
| Warehouse Plan | Plan used for candidates and walk distance |
| Warehouse (optional) | Limit scope to a branch warehouse and its descendants (for example a refrigerator group) |
| From Date / To Date | Stock Ledger window used for Heat and Qty Moved |

Rows are ordered by activity: highest Heat first, then Qty Moved, then item code. Priority on the row matches that rank (1 = hottest).

## Columns

| Column | Meaning |
|--------|---------|
| Heat | Number of stock movements for the item in scope and date range (distinct voucher activity, not a temperature metaphor) |
| Qty Moved | Total quantity moved in stock UOM over the same window — demand/activity, **not** how much a bin holds |
| Current Default Warehouse | Item Default warehouse for the company, if any |
| Putaway Rule / Putaway Warehouse | Active Putaway Rule with the lowest priority number for that item and company |
| Suggested Warehouse | Proposed leaf storage location |
| Slot Capacity | How many units of the item (stock UOM) fit in the suggested warehouse interior, from dimensions |
| Fit Status | `fits`, `no_fit`, or `unverified` (missing or incomplete dimensions) |
| Score | Location score used when comparing candidates (lower is better before custom hooks) |
| Priority | Suggestion rank; used as Putaway Rule priority when you apply Create Putaway Rule |

**Fit Status = fits** means at least one unit fits in the bin. It does not mean the bin can hold the full Qty Moved. Slot Capacity is the physical hold of that slot.

## How suggestions are chosen

1. Resolve warehouses in scope (company + plan, optionally under a branch warehouse).
2. Compute Heat and Qty Moved from Stock Ledger Entries in that scope and date range.
3. Build candidate leaf warehouses on the plan (groups and excluded warehouse types such as Transit are skipped).
4. Rank items by Heat (then Qty Moved).
5. Assign hotter items to nearer plan slots in walk-distance order: each item claims the next candidate that is not `no_fit`.

So suggestions spread across nearby bins rather than stacking every hot item into the single closest location.

## Applying suggestions

Select one or more rows with a Suggested Warehouse, then use **Apply**:

### Set Default Warehouse

Updates the Item Default warehouse for the company to the suggested warehouse.

### Create Putaway Rule

Creates a Putaway Rule (or updates an existing rule for the same item, warehouse, and company) with:

- Warehouse = Suggested Warehouse
- Priority = report Priority
- Capacity = report **Slot Capacity** (physical fit), adjusted upward if needed so ERPNext validation still passes when stock is already on hand

Rows without Slot Capacity are blocked until you add dimensions and refresh the report. There is no separate capacity prompt.

## Configuration

### Inventory Tools Settings → Warehouse Slotting

| Field | Effect |
|-------|--------|
| Require Plan for Location Suggestion | When enabled (default), only warehouses placed on the Warehouse Plan with coordinates are candidates |
| Excluded Warehouse Types | Comma-separated Warehouse Types skipped as candidates (default includes Transit) |

### Multi-company Purchase Receipts

Under purchasing / multi-company options:

| Field | Effect |
|-------|--------|
| Apply Putaway Rule on Multi-Company Purchase Receipt | When enabled (default), Purchase Receipts created from a multi-company Purchase Order via **Create Purchase Receipts** are saved with **Apply Putaway Rule** checked. Turn off if you receive to the Material Request warehouse and put away later with a Stock Entry |

Requesting company on Purchase Order Item is used to split receipts by company; putaway then uses that company’s rules.

## Dimensions and capacity

Slot Capacity uses:

- Item exterior dimensions (resolved to stock UOM when conversion exists)
- Warehouse interior dimensions
- Floor packing, and volume when both item and warehouse have height

If dimensions are missing or incomplete, Fit Status is `unverified` and capacity is empty. Cartonization and this report share the same Physical Dimension data; keeping exteriors and interiors realistic avoids absurdly low capacities (for example treating a pound of fruit as a meter-scale box).

## Extending the score (developers)

Apps can register hooks named `warehouse_location_score`. Each hook receives `(item_code, warehouse, score, context)` and returns a new score. Use this to bias or exclude locations beyond walk distance and fit or to introduce other business logic requirements.
