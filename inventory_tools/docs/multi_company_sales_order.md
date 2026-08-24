<!-- Copyright (c) 2024, AgriTheory and contributors
For license information, please see license.txt-->

# Multi-Company Sales Order

<div class="byline">
  Tyler Matteson 2026-05-07
</div>


## Overview

In multi-company ERPNext setups, a parent company may fulfill customer orders using inventory from multiple subsidiary companies. The standard ERPNext validation requires that all warehouses in a Sales Order belong to the same company as the Sales Order itself. This feature relaxes that constraint when the `Multi-Company Sales Order` flag is enabled.

## How It Works

When a Sales Order has the `Multi-Company Sales Order` checkbox enabled:

1. **Warehouse Validation**: The system skips the company-warehouse validation, allowing warehouses from different companies to be used in the same Sales Order
2. **Quotation Validation**: The system skips company matching validation against linked Quotations, enabling cross-company order fulfillment

This allows a central sales company to create orders that draw inventory from multiple subsidiaries while maintaining proper audit trails and accounting.

## Use Cases

### Centralized Sales with Distributed Inventory

A holding company manages sales for multiple subsidiaries. When a customer places an order, the sales team can fulfill it using inventory from whichever subsidiary has the items in stock, without creating separate orders for each company.

### Regional Fulfillment

A company with regional warehouses under different legal entities can fulfill orders from the nearest location to the customer, regardless of which company owns that warehouse.

### Inter-Company Transfers

Combined with ERPNext's inter-company transaction features, this enables seamless order fulfillment across company boundaries while maintaining proper financial records.

