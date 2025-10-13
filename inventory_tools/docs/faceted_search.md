<!-- Copyright (c) 2024, AgriTheory and contributors
For license information, please see license.txt-->


# Faceted Search

<div class="byline">
  Rohan Bansal, Devarsh Bhatt, Heather Kusmierz, and Tyler Matteson 2024-08-12
</div>


Faceted search works on top of ERPNext's Shopping Cart to add additional Ecommerce controls for marketplace users. This feature allows you to list your products under `/all-products` and filter them based on their specifications.

# Manual Setup

Follow the steps to create your first listed product with multiple specifications and their variations.

### Steps:

1. Items and Website Items should be configured according to the instructions provided for the [Ecommerce Module](https://docs.erpnext.com/docs/user/manual/en/set_up_e_commerce)

2. To create Specifications for the Item:
   1. Type `Specification` in Awesomebar > `Add Specification`.
   2. Select `DocType` on which you would like to customize the specification.
   3. Select `Apply On` based on the doctype or leave it blank to apply to all records of that DocType. This currently only works for Item.
   4. Mark it `Enabled`.
![Screen shot of ](./assets/specification.PNG)

   5. Under `Attributes` table click `Add Row` > `Edit`.

      - Write unique `Attribute Name`.
      - Choose if the value is expected to be a `Date Value` or `Numeric Value`.
      - Select `Apply On` (In this case, we can choose `Item`).
      - Optionally select the `Field` on which the attribute should be applied.
      - Choose a `Component` based on the following criteria:
        
          1. `FacetedSearchColorPicker`: if the attribute is related to colors.
          2. `FacetedSearchDateRange`: if the attribute is related to date values.
          3. `FacetedSearchNumericRange`: if the attribute is related to numeric values.
          4. `AttributeFilter`: if the attribute doesn't belong to any of the above.
![Screen shot of ](./assets/specification_attribute.PNG)

      - `Save` the Specification(s).
7. Create `Specification Values`:
   - Route through `Stock` > `Item` > Choose Item.
   - On Item page click `Actions` (Top Right) >  Click `Edit Specification`
      - This will try to pre-populate the specifications based on your selection. If no specifications are set, please select from the dropdown instead.
   - `Save`
![Screen shot of ](./assets/edit_specifications.PNG)


This is how you can create and manage your specification. you can go to `/all-products`, you will see listed Item and Filter(s) on left.

### Note:
`Specification` and `Specification Values` are reusable as long as the grouping of Items is done correctly. You may want to create new Specifications for different types of goods.