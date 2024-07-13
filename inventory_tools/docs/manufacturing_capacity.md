<!-- Copyright (c) 2024, AgriTheory and contributors
For license information, please see license.txt-->

# Manufacturing Capacity Report

Manufacturing Capacity is a report-based interface that, given a BOM and Warehouse, displays the demand and in-stock quantities for the entire hierarchy of any BOM tree containing that BOM.

Once the filters are set, the report traverses the BOM tree to find the top-level parents of the given BOM. From there, it finds total demand based on outstanding Sales Orders, Material Requests (of type "Manufacture"), and Work Orders, adjusting for any overlap. In stock quantities for each level are determined based on the selected Warehouse. The Parts Can Build quantity is based on what is in stock (for non-BOM/raw material rows) or the minimum Parts can Build of sub-levels for BOM rows.

The Parts Can Build Qty is slightly different for non-BOM vs BOM rows. For non-BOM (raw material) rows, it's the In Stock Qty divided by the Qty per Parent BOM. For BOM rows, it's the minimum of the Parts Can Build for all sub-assemblies. So if a BOM row requires a raw material that isn't in stock, it will show 0 Parts Can Build Qty, even if there are other sub assemblies in stock.

The Difference Qty calculation is also different for non-BOM and BOM rows. Since non-BOM rows account for the In Stock Qty in the Parts Can Build Qty number, the Difference Qty is the Parts Can Build less the Demanded Qty. For BOM rows, since the Parts Can Build Qty is based off available sub-assembly item quantities (and doesn't use the In Stock Qty in that calculation), the Difference Qty is the In Stock Qty plus Parts Can Build Qty less the Demanded Qty.

![Screen shot showing the Manufacturing Capacity report output for the Ambrosia Pie BOM and all Warehouses. There are rows for all levels of the BOM hierarchy - the Pie itself, sub-level rows for each sub-assembly of the Pie Crust and Pie Filling, with rows below each of those for the raw materials comprising each BOM. Columns include the BOM, Item, Description, Quantity per Parent BOM, BOM UoM, Demanded Quantity, In Stock Quantity, Parts Can Build quantity, and the Difference Quantity (demanded quantity less parts can build quantity).](./assets/manufacturing_capacity_report.png)
