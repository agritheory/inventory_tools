# Warehouse Path
ERPNext allows its user to construct hierarchial abstractions for their physical facilities. This can make it difficult to know when you are selecting a warehouse if it is "Bin A" in the "Storage Closet" or if is "Bin A" from the "Repair Supplies" warehouse.

This feature encodes the warehouse hierarchy into a string, which becomes searchable, and allows the user to more easily understand which warehouse they are selecting.

## Example
In this example there are two warehouses that start with "Refridger..." and while they are different, they could be mixed up.

![warehouse tree](assets/warehouse_tree.png)

In the Link dropdown, the full path is given, omitting the root "All Warehouses - APC" and the company abbreviation at each level. 

![warehouse dropdown](assets/fridge.png)

This view shows the user-provided search text of "Refr..." matches the two similarly-named warehouses. The warehouse path under each option's name clearly distinguishes the choices by specifying each warehouse's hierarchy.
