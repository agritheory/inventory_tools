# Inventory Tools Documentation

The Inventory Tools application enhances and extends inventory-related functionality and workflows in ERPNext. It includes the following features:

- **[Material Demand](./material_demand.md)**: a report-based interface to aggregate required Items across multiple sources, then optionally create Purchase Orders or Request for Quotations
- **[UOM Enforcement](./uom_enforcement.md)**: for doctypes that have an Items table or Unit of Measure (UOM) fields, this feature restricts the user's options from arbitrary selections to only UOMs defined in the Item master with a specified conversion factor
- **[Warehouse Path](./warehouse_path.md)**: for any warehouse selection field, this features helps clearly identify warehouses by creating a warehouse path and adding a human-readable string under the warehouse name in the format "parent warehouse(s)->warehouse"
- **[Subcontracting Workflow via Work Order](./wo_subcontracting.md)**: an alternative to ERPNext's subcontracting workflow that enables a user to employ Work Orders, subcontracting Purchase Orders, and manufacturing Stock Entries in lieu of Purchase Receipts or Subcontracting Orders/Receipts. Enhancements to the subcontracting Purchase Invoice allow a user to quickly reconcile what Items have been received with what is being invoiced
- **[Inline Landed Costing](./landed_costing.md)**: Coming soon! This features enables a user to include any additional costs to be capitalized into an Item's valuation directly in a Purchase Receipt or Purchase Invoice without needing to create a separate Landed Cost Voucher
- **[Manufacturing Capacity](./manufacturing_capacity.md)**: a report-based interface to show, for a given BOM, the entire hierarchy of any BOM tree containing that BOM with demand and in-stock quantities for all levels

## Configuration
Any feature in Inventory Tools may be toggled on or off via the Inventory Tools Settings document. The only exception to this is the Material Demand report, which is generally available upon installation of the app. There may be one settings document for each company in ERPNext to enable features on a per-company basis. Follow the links above for further details around feature-specific configuration.

![Screen shot of ](./assets/settings.png)

## Installation
Full [installation instructions](https://github.com/agritheory/inventory_tools) can be found on the application's repository.

Note that the application includes a script to install example data to experiment and test the app's features. See the [Using the Example Data to Experiment with Inventory Tools page](./exampledata.md) for more details.
