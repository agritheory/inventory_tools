<!-- Copyright (c) 2024, AgriTheory and contributors
For license information, please see license.txt-->

# Overproduction Allowance

<div class="byline">
  Rohan Bansal, coleandreoli, Heather Kusmierz, Tyler Matteson, and Francisco Roldán 2026-02-22
</div>


## Overview

Manufacturing processes often produce slightly more or fewer items than planned due to process variability, yield differences, or operational efficiency. The Overproduction Allowance feature allows you to configure an acceptable percentage above the planned quantity that can be manufactured without triggering validation errors.

This feature extends ERPNext's standard overproduction percentage setting by allowing configuration at multiple levels with a clear precedence hierarchy.

## Configuration Precedence

The overproduction allowance percentage is determined using the following priority (highest to lowest):

1. **BOM Level**: The `Overproduction Percentage for Work Order` field on the Bill of Materials
2. **Company Level**: The `Overproduction Percentage for Work Order` field in Inventory Tools Settings
3. **Global Level**: Falls back to ERPNext's Manufacturing Settings if no company-specific setting exists

This hierarchy allows you to set a default allowance for your company while overriding it for specific BOMs that may have different yield characteristics.

## Where Overproduction Is Enforced

The overproduction allowance is validated across multiple manufacturing documents:

### Work Order

- Validates that manufactured and transferred quantities don't exceed the Work Order quantity plus allowance
- Validates that operation completed quantities stay within the allowed threshold
- Displays the current overproduction percentage when the Work Order is loaded

### Job Card

- Validates that the total completed quantity doesn't exceed the quantity to manufacture plus the allowance percentage
- Allows partial completion while preventing over-manufacturing

### Stock Entry

- **Material Transfer for Manufacture**: Validates that transferred quantities don't exceed what's needed for the allowed production quantity
- **Manufacture**: Validates that the finished goods quantity doesn't exceed the Work Order quantity plus allowance
- Checks that cumulative production (current entry plus already produced) stays within limits

## Configuration

### Company-Level Setting

Navigate to **Inventory Tools Settings** for your company and set the `Overproduction Percentage for Work Order` field.

For example, setting this to `10` allows manufacturing up to 110% of the planned quantity.

### BOM-Level Setting

For BOMs with specific yield characteristics, set the `Overproduction Percentage for Work Order` field directly on the BOM. This value takes precedence over the company setting.

## Example

Consider a Work Order to manufacture 100 units with a 10% overproduction allowance:

| Scenario | Allowed? | Reason |
|----------|----------|--------|
| Manufacture 100 units | Yes | Within planned quantity |
| Manufacture 105 units | Yes | Within 10% allowance (max 110) |
| Manufacture 110 units | Yes | At maximum allowed |
| Manufacture 111 units | No | Exceeds 10% allowance |

## Error Messages

When overproduction limits are exceeded, you'll see validation errors such as:

- "Quantity manufactured in this Job Card of {X} plus quantity already produced for Work Order {WO} of {Y} is greater than the Work Order's quantity to manufacture of {Z} plus the overproduction allowance of {N}%"
- "For quantity {X} should not be greater than work order quantity {Y}"

These messages help identify exactly where the limit was exceeded and by how much.
