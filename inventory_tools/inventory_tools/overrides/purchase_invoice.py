# Copyright (c) 2023, AgriTheory and Contributors
# See license.txt
import json

import frappe
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from frappe.utils.data import cint


class InventoryToolsPurchaseInvoice(PurchaseInvoice):
	def validate_with_previous_doc(self):
		config = {
			"Purchase Order": {
				"ref_dn_field": "purchase_order",
				"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
			},
			"Purchase Order Item": {
				"ref_dn_field": "po_detail",
				"compare_fields": [["project", "="], ["item_code", "="], ["uom", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True,
			},
			"Purchase Receipt": {
				"ref_dn_field": "purchase_receipt",
				"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
			},
			"Purchase Receipt Item": {
				"ref_dn_field": "pr_detail",
				"compare_fields": [["project", "="], ["item_code", "="], ["uom", "="]],
				"is_child_table": True,
			},
		}
		pos = list({r.purchase_order for r in self.items})
		if len(pos) == 1 and frappe.get_value("Purchase Order", pos[0], "multi_company_purchase_order"):
			config["Purchase Order"]["compare_fields"] = [["currency", "="]]

		super(PurchaseInvoice, self).validate_with_previous_doc(config)

		if (
			cint(frappe.get_cached_value("Buying Settings", "None", "maintain_same_rate"))
			and not self.is_return
			and not self.is_internal_supplier
		):
			self.validate_rate_with_reference_doc(
				[
					["Purchase Order", "purchase_order", "po_detail"],
					["Purchase Receipt", "purchase_receipt", "pr_detail"],
				]
			)
