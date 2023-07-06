import frappe
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
from frappe import _


class CustomPurchaseOrder(PurchaseOrder):
	def validate(self):
		# settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		# if self.is_subcontracted and settings and settings.enable_work_order_subcontracting:
		# 	for item in self.items:
		# 		if not item.get():
		# 			frappe.throw(
		# 					_("Row #{0}: Work Order is not specified for item {1}").format(
		# 						item.idx, item.item_code
		# 					)
		# 				)

		super().validate()  # TODO: modify the existing subcontracting checks?


"""
- Depends On and Mandatory Depends on code example from fg_item in PO Item:
eval:parent.is_subcontracted && !parent.is_old_subcontracting_flow


"""
