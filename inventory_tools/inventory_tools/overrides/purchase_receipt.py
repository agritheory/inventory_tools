# Copyright (c) 2023, AgriTheory and Contributors
# See license.txt


import frappe
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
from frappe.utils.data import cint


class InventoryToolsPurchaseReceipt(PurchaseReceipt):
	def validate_with_previous_doc(self):
		"""
		HASH: 9daabfca8a3dc4d940d02bf218cfd02605dbde0f
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

	def validate_qi_presence(self, row):
		settings = frappe.get_doc("Inventory Tools Settings", self.company)

		if settings.enable_quarantine_workflow:
			return

		super().validate_qi_presence(row)

	def validate_qi_submission(self, row):
		settings = frappe.get_doc("Inventory Tools Settings", self.company)

		if settings.enable_quarantine_workflow:
			return

		super().validate_qi_submission(row)


def handle_pr_quarantine(doc, method):
	settings = frappe.get_doc("Inventory Tools Settings", doc.company)

	if not settings.enable_quarantine_workflow:
		return

	for row in doc.items:
		if frappe.db.get_value("Item", row.item_code, "inspection_required_before_purchase"):
			if not row.intended_warehouse:
				row.intended_warehouse = row.warehouse

			qi_template = frappe.db.get_value("Item", row.item_code, "quality_inspection_template")

			quarantine_wh = None

			if qi_template:
				quarantine_wh = frappe.db.get_value(
					"Quality Inspection Template", qi_template, "quarantine_warehouse"
				)

			quarantine_wh = quarantine_wh or settings.default_quarantine_warehouse

			if not quarantine_wh:
				frappe.throw(f"No Quarantine Warehouse configured for Item {row.item_code}")

			row.warehouse = quarantine_wh
			row.quality_inspection = None
