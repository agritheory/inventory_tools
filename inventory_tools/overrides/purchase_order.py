import frappe
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
from frappe import _


class CustomPurchaseOrder(PurchaseOrder):
	def validate(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		sub_wo = self.get("subcontracting")
		if self.is_subcontracted and settings and settings.enable_work_order_subcontracting and sub_wo:
			items_fg_qty = sum(item.get("fg_item_qty") or 0 for item in self.get("items"))
			subc_fg_qty = sum(row.get("fg_item_qty") or 0 for row in sub_wo)
			diff = abs(items_fg_qty - subc_fg_qty)
			if diff > 1:  # TODO: use different precision?
				frappe.msgprint(  # Just a warning in case a PO is created before WO's exist, then several WOs needed to complete the work so each one has less than PO
					msg=_(
						f"The total of Finished Good Item Qty for all items does not match the total Finished Good Item Qty in the Subcontracting table. There is a difference of {diff}."
					),
					title=_("Warning"),
					indicator="red",
				)

		super().validate()  # TODO: modify the existing subcontracting checks?
