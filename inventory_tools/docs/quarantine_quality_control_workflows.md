<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Quarantine Quality Control

<div class="byline">
  IshwaryaM1030 and Tyler Matteson 2026-03-03
</div>


## Overview

The Quarantine Quality Control feature allows inventory to be automatically moved to a quarantine warehouse for inspection, rather than requiring immediate quality checks during receipt or manufacturing. Items remain in quarantine until quality inspection is completed and approved.

**Key Benefit**: Separates the receiving/manufacturing process from quality inspection, improving operational efficiency while maintaining quality control.

## Setup

### 1. Enable the Feature

Navigate to **Inventory Tools Settings** and enable **Enable Quarantine Workflow**.

Optionally, set a **Default Quarantine Warehouse** as a fallback for items whose Quality Inspection Template does not specify a quarantine location.

To prevent stock from leaving a quarantine warehouse through any means other than an accepted Quality Inspection, also enable **Block Issue from Quarantine**. See [Blocking Manual Removals](#blocking-manual-removals) below.

### 2. Configure Quality Inspection Templates

For each template requiring quarantine workflow:

1. Open **Quality Inspection Template**
2. Set the **Quarantine Warehouse** field to your designated quarantine location
3. Configure inspection parameters as needed
4. Save the template

### 3. Configure Items

Quality Inspection Template assignment and inspection requirements are configured at two levels:

- **Quality Inspection Template**: Set on the **Item** master. This determines which inspection parameters apply and which quarantine warehouse to use (overriding the default).
- **Inspection Required flags**: Set on **Item Default** (company-scoped). Item-level inspection fields are hidden.

On **Item Default** for each company and item:

1. Check **Inspection Required Before Purchase** (for incoming materials via Purchase Receipt or Subcontracting Receipt)
2. Check **Inspection Required Before Delivery** (for outgoing goods)
3. Check **Inspection Required Before Manufacture** (for raw materials transferred to production)

## Workflow

### Receiving Items (Purchase Receipt)

1. Create and submit **Purchase Receipt**
2. System automatically routes items with `inspection_required_before_purchase` (Item Default) to the quarantine warehouse
3. Items remain in quarantine until inspection is complete

### Receiving Subcontracted Items (Subcontracting Receipt)

Subcontracting Receipts follow the same routing logic as Purchase Receipts. Items with `inspection_required_before_purchase` set on their Item Default are automatically redirected to the quarantine warehouse on submit.

### Material Transfer for Manufacture

For Stock Entry type **Material Transfer for Manufacture**, items with `inspection_required_before_manufacture` (Item Default) are routed to the quarantine warehouse instead of the production warehouse. The original target warehouse is saved as `Intended Warehouse` on the Stock Entry row and used when releasing the stock after a passed inspection.

### Inspecting Items

1. Open the **Quality Inspection** record linked to the Purchase Receipt, Subcontracting Receipt, or Stock Entry
2. Record test results and observations
3. Set status to **Accepted** or **Rejected** and submit

### Releasing from Quarantine

Once a Quality Inspection has been submitted with status **Accepted**, a **Release from Quarantine** button appears on the form. Clicking it creates a draft **Stock Entry** (Material Transfer) for review:

- **Source**: The quarantine warehouse (determined from the originating Stock Ledger Entry)
- **Target**: The final destination warehouse (the `intended_warehouse` recorded on the reference document's item row)
- **Quantity**: Full received/transferred quantity — not the inspection `sample_size`
- **Company**: Inherited from the reference document

Review the draft Stock Entry and submit it to complete the transfer. The draft carries the Quality Inspection as a reference on each item row, which is how **Block Issue from Quarantine** (see below) knows to allow the transfer through.

If no `intended_warehouse` is recorded on the reference document (e.g. stock was moved to quarantine manually without going through the standard receipt workflow), clicking the button will raise an error. Create the transfer from quarantine manually in that case.

## Blocking Manual Removals

Enable **Block Issue from Quarantine** in **Inventory Tools Settings** to prevent stock from being manually removed from any configured quarantine warehouse outside of the QI-driven release workflow.

When this setting is active, any Stock Entry submission where the source warehouse is a quarantine warehouse will be blocked — **unless** the Stock Entry row carries a Quality Inspection reference (i.e. it was created via the **Release from Quarantine** button on an accepted QI). This allows those release transfers to proceed while blocking ad-hoc issues and transfers.

Quarantine warehouses are identified by comparing against:
- The **Default Quarantine Warehouse** on Inventory Tools Settings
- The **Quarantine Warehouse** field on any Quality Inspection Template

## Use Cases

**Food Processing**: Raw ingredients tested for contamination before use in production

**Pharmaceuticals**: Manufactured tablets held for potency testing before release

**Manufacturing**: Electronic components verified before assembly

## Key Reports

- **Stock Balance**: Filter by quarantine warehouse to see pending items
- **Quality Inspection**: Track inspection status and results
- **Stock Ledger**: Audit complete movement history

