<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Generic Items

Generic items are non-stock Items used as placeholders on Purchase Material Requests. Buyers can replace them with one or more specific items on the Purchase Order while keeping the link back to the original request line.

## Configuration

1. Open **Inventory Tools Settings** for the company and enable **Enable Generic Items**.
2. On an Item, check **Is Generic Item**. This field is available only when **Maintain Stock** is unchecked.

## Purchase workflow

1. Create a Material Request with a generic item (for example, "Miscellaneous Office Supplies").
2. Create a Purchase Order from the Material Request.
3. Change the item on one or more PO lines to the actual products being purchased. The Material Request link is preserved.
4. Submit the Purchase Order.

Several PO lines may reference the same generic Material Request line (for example, one request for "misc supplies" fulfilled as paper, tape, and pens on separate lines).

## Ordered progress

For generic Material Request lines, **per ordered** is driven by **amount**, not quantity:

- Submitted PO lines linked to the request contribute their **base net amount** toward the request line's **amount**.
- When the summed PO amount reaches the request line amount, the line is fully ordered.

Non-generic lines continue to use ERPNext's quantity-based rules.

## Material Demand

The **Material Demand** report lists generic request lines with a **Generic** label on the item. POs created from the report still start with the generic item; swap items on the draft PO before submit.
