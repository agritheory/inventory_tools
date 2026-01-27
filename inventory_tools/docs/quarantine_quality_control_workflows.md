<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Quarantine Quality Control

<div class="byline">
  Ishwarya 2026-01-12
</div>


## Overview

The Quarantine Quality Control feature allows inventory to be automatically moved to a quarantine warehouse for inspection, rather than requiring immediate quality checks during receipt or manufacturing. Items remain in quarantine until quality inspection is completed and approved.

**Key Benefit**: Separates the receiving/manufacturing process from quality inspection, improving operational efficiency while maintaining quality control.

## Setup

### 1. Enable the Feature

Navigate to **Inventory Tools Settings** and enable **Quarantine Quality Control**.

### 2. Configure Quality Inspection Templates

For each template requiring quarantine workflow:

1. Open **Quality Inspection Template**
2. Set the **Quarantine Warehouse** field to your designated quarantine location
3. Configure inspection parameters as needed
4. Save the template

### 3. Configure Items

On the **Item** master:

1. Assign the appropriate **Quality Inspection Template**
2. Check **Inspection Required Before Purchase** (for incoming materials)
3. Check **Inspection Required Before Delivery** (for finished goods)

## Workflow

### Receiving Items

1. Create and submit **Purchase Receipt**
2. System automatically routes items to the quarantine warehouse
3. Items remain in quarantine until inspection is complete

### Inspecting Items

1. Open the **Quality Inspection** record
2. Record test results and observations
3. Mark as **Accepted** or **Rejected**

### Releasing from Quarantine

1. On submit of Quality Inspection, system automatically creates **Stock Entry** (Material Transfer)
2. Source: Quarantine warehouse
3. Target: Final destination warehouse
4. System validates that quality inspection passed and Transfers the stock from Quarantine warehouse to Final destination warehouse

**Note**: Items cannot be removed from quarantine if inspection is pending or failed.

## Use Cases

**Food Processing**: Raw ingredients tested for contamination before use in production

**Pharmaceuticals**: Manufactured tablets held for potency testing before release

**Manufacturing**: Electronic components verified before assembly

## Key Reports

- **Stock Balance**: Filter by quarantine warehouse to see pending items
- **Quality Inspection**: Track inspection status and results
- **Stock Ledger**: Audit complete movement history

