# Inline Landed Costing

This features enables a user to directly include any additional costs to be capitalized into an Item's valuation in a Purchase Receipt or Purchase Invoice without needing to create a separate Landed Cost Voucher.

By default, this feature is turned off, but may be toggled on by checking the Enable Inline Landed Costing checkbox in the Landed Costing Section in the Inventory Tools Settings document. As with all Inventory Tools Settings, these are set on a per-company basis.

![Screen shot of the Inventory Tools Settings document for Ambrosia Pie Company showing the Enable Landed Costing box checked.](./assets/inventory_tools_settings_inline_lc.png)

When the feature is on, the Purchase Receipt and Purchase Invoice documents will show an additional dropdown field called Distribute Landed Cost Charges Based On above the Items table. If there are no landed costs in the document, then the default Don't Distribute should remain selected. To include and distribute landed costs, the landed costs should be entered as row(s) into the Purchase Taxes and Charges table. The method to distribute landed costs may be based on the relative items' Qty or Amount.

![Screen shot of a Purchase Receipt showing Distribute Charges Based On selection of Amount. There's one row in the Purchase Taxes and Charges table for landed costs of $10.00. The items table has additional columns showing the split of the landed costs based on the item amounts.](./assets/inline_lc_pr_with_lc.png)

Note that including landed costs in an item's valuation only works when it is marked as an asset or stock item in its Item master.

The feature assumes all rows in the Purchase Taxes and Charges table should be included and distributed as landed costs. If there are any rows that should be excluded (such as sales tax or a discount), then the user can click on the Edit field for the row, and change the Consider Tax or Charge For field to "Total".

![Screen shot of the edit form for a row in the Purchase Taxes and Charges table where the Consider Tax or Charge For field dropdown selection is being changed from Valuation and Total to Total since that row is not a landed cost.](./assets/inline_lc_change_category_of_non_lc.png)


## Avoid Double-Counting Landed Costs in a Purchase Invoice

In the event that a user includes landed costs in a Purchase Receipt, then creates a Purchase Invoice from that document, some adjustments are necessary to make sure the landed costs from the Purchase Receipt aren't included a second time in the item's valuation in the Purchase Invoice.

Set the Distribute Landed Cost Charges Based On selection to Don't Distribute. This change will remove landed costs from the items since they're already included via the Purchase Receipt. Under the hood, it resets the Consider Tax or Charge For field for each row in the Purchase Taxes and Charges table to Total. If that value were Valuation and Total, it would flag the row's amount to be included in the items' valuation rates. If this change isn't made, then the landed costs would be included a second time in the item valuation rates via the Purchase Invoice, thus double-counting them.

Note that changing the selection in the Distribute Landed Cost Charges Based On field back to either Qty or Amount will update all rows in the Purchase Taxes and Charges table so they're included in item landed costs and flipping it back to Don't Distribute will excludes all rows from item landed costs.

![Screen shot of the Distribute Landed Cost Charges Based On drop down selection set to Don't Distribute.](./assets/inline_lc_dont_distribute.png)
