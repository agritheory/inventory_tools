<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Generic Items

<div class="byline">
  Tyler Matteson 2026-11-04
</div>


Generic items are non-stock placeholder Items for things that don't have an Item yet. A requester who can't find what they need adds a generic item to a Purchase Material Request and describes it (for example, with a link to the product). A purchasing agent or Item Manager then creates the specific Item correctly and puts it on the Purchase Order in place of the generic item.

## Configuration

1. Open **Inventory Tools Settings** for the company and enable **Enable Generic Items**.
2. Set **Generic Item Quantity Mismatch** to **Ignore**, **Warn** (default), or **Error**. This controls what happens when the Purchase Order line replacing a generic item has a different quantity than the Material Request line.
3. On an Item, check **Is Generic Item**. This field is available only when **Maintain Stock** is unchecked, and is hidden entirely unless at least one company has generic items enabled.

## Purchase workflow

1. Create a Material Request with a generic item (for example, "Miscellaneous Supplies") and describe what is needed.
2. Create a Purchase Order from the Material Request.
3. On the draft Purchase Order, change the item on the line to the specific item being purchased. The Material Request link is preserved. Each generic Material Request line can be replaced by only one Purchase Order line.
4. Submit the Purchase Order.

On submit, the Material Request line is updated to the purchased item: item code, name, UOM, quantity, and rate are copied from the Purchase Order line, and the original placeholder is kept in the line's **Generic Item** field. From then on, the Material Request line behaves like any other line for the purchased item, including ordered progress and requested quantity. Cancelling the Purchase Order does not restore the generic item.

## Where generic items are allowed

A generic item is a placeholder, so it can only appear on Material Requests and draft Purchase Orders. A Purchase Order that still has a generic line cannot be submitted. Saving any of the following with a generic item is rejected: Purchase Receipt, Purchase Invoice, Sales Invoice, Delivery Note, Stock Entry, Stock Reconciliation, Pick List, Subcontracting Order, Subcontracting Receipt, Request for Quotation, and Supplier Quotation.

Generic items never create Item Prices, either automatically from a transaction or by hand.

## Material Demand

The **Material Demand** report lists generic request lines with a **Generic** label and the requester's description on the item. Each generic line's demand is its own quantity rather than the total across all generic requests. POs created from the report start with the generic item and the request's description; swap the item on the draft PO before submitting. Generic lines cannot be sent out as Requests for Quotation.
