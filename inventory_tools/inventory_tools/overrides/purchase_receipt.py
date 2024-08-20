# Copyright (c) 2023, AgriTheory and Contributors
# See license.txt


import frappe
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
from frappe.utils.data import cint


class InventoryToolsPurchaseReceipt(PurchaseReceipt):
	def validate_with_previous_doc(self):
		"""
		HASH: 427439c3f19bfd1401628cf39a30ddd291dbfec7
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/stock/doctype/purchase_receipt/purchase_receipt.py
		METHOD: validate_with_previous_doc
		"""

		config = {
			"Purchase Order": {
				"ref_dn_field": "purchase_order",
				"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
			},
			"Purchase Order Item": {
				"ref_dn_field": "purchase_order_item",
				"compare_fields": [["project", "="], ["uom", "="], ["item_code", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True,
			},
		}

		pos = list({r.purchase_order for r in self.items})
		if len(pos) == 1 and frappe.get_value("Purchase Order", pos[0], "multi_company_purchase_order"):
			config["Purchase Order"]["compare_fields"] = [["supplier", "="], ["currency", "="]]
		super(PurchaseReceipt, self).validate_with_previous_doc(config)

		if (
			cint(frappe.db.get_single_value("Buying Settings", "maintain_same_rate"))
			and not self.is_return
			and not self.is_internal_supplier
		):
			self.validate_rate_with_reference_doc(
				[["Purchase Order", "purchase_order", "purchase_order_item"]]
			)
