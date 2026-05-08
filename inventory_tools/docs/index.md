<!-- Copyright (c) 2024, AgriTheory and contributors
For license information, please see license.txt-->

# Inventory Tools Documentation

<div class="byline">
  AgriTheory 2026-03-26
</div>


The Inventory Tools application enhances and extends inventory-related functionality and workflows in ERPNext. It includes the following features:

- **[Material Demand](./material_demand.md)**: a report-based interface to aggregate required Items across multiple sources, then optionally create Purchase Orders or Request for Quotations
- **[Warehouse Path](./warehouse_path.md)**: for any warehouse selection field, this features helps clearly identify warehouses by creating a warehouse path and adding a human-readable string under the warehouse name in the format "parent warehouse(s)->warehouse"
- **[Quotation Demand](./quotation_demand.md)**: a report-based interface to aggregate required Items across multiple Quotations, Customers, and Companies, then create draft Sales Orders
- **[Warehouse Path](./warehouse_path.md)**: for any warehouse selection field, this feature helps clearly identify warehouses by creating a warehouse path and adding a human-readable string under the warehouse name in the format "parent warehouse(s)->warehouse"
- **[Warehouse Plan](./warehouse_plan.md)**: optimizes pick list walking paths within a warehouse using a 2D floor plan representation and shortest-path algorithms, with support for FIFO, LIFO, and bin depletion strategies
- **[Subcontracting Workflow via Work Order](./wo_subcontracting.md)**: an alternative to ERPNext's subcontracting workflow that enables a user to employ Work Orders, subcontracting Purchase Orders, and manufacturing Stock Entries in lieu of Purchase Receipts or Subcontracting Orders/Receipts. Enhancements to the subcontracting Purchase Invoice allow a user to quickly reconcile what Items have been received with what is being invoiced
- **[Inline Landed Costing](./landed_costing.md)**: Coming soon! This feature enables a user to include any additional costs to be capitalized into an Item's valuation directly in a Purchase Receipt or Purchase Invoice without needing to create a separate Landed Cost Voucher
- **[Manufacturing Capacity](./manufacturing_capacity.md)**: a report-based interface to show, for a given BOM, the entire hierarchy of any BOM tree containing that BOM with demand and in-stock quantities for all levels
- **[Workstation Operating Cost](./workstation_operating_cost.md)**: a flexible, time-based system for tracking and allocating manufacturing overhead to production operations with historical cost periods and detailed cost breakdowns
- **[Faceted Search](./faceted_search.md)**: loosely-coupled attributes for Items, visible in both Ecommerce and Item Listview search contexts
- **[Alternate Workstation](./alternate_workstation.md)**: allows selecting alternative workstations that can perform the same operation
- **[Cartonization](./cartonization.md)**: Cartonization ensures that items involved in inventory transactions physically fit into their 
target containers
- **[Quarantine Quality Control](./quarantine_quality_control_workflows.md)**: allows inventory to be automatically moved to a quarantine warehouse for inspection, Items remain in quarantine until quality inspection is completed and approved
- **[Overproduction Allowance](./overproduction_allowance.md)**: configurable percentage allowance for manufacturing more than the planned Work Order quantity, with validation across Work Orders, Job Cards, and Stock Entries
- **[Multi-Company Sales Order](./multi_company_sales_order.md)**: enables Sales Orders to use warehouses from multiple companies, supporting centralized sales with distributed inventory fulfillment
- **[UOM Category curation](./uom_category_curation.md)**: overview and bulk enable/disable helpers on **UOM Category** for Units of Measure that appear only on conversion factors for that category versus Item, transactional, and cross-category usage

## Configuration
Any feature in Inventory Tools may be toggled on or off via the Inventory Tools Settings document. The only exception to this is the Material Demand report, which is generally available upon installation of the app. There may be one settings document for each company in ERPNext to enable features on a per-company basis. Follow the links above for further details around feature-specific configuration.

![Screen shot of ](./assets/settings.png)

## Installation
Full [installation instructions](https://github.com/agritheory/inventory_tools) can be found on the application's repository.

Note that the application includes a script to install example data to experiment and test the app's features. See the [Using the Example Data to Experiment with Inventory Tools page](./exampledata.md) for more details.
