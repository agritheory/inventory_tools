# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.subcontracting.doctype.subcontracting_receipt.subcontracting_receipt import (
	SubcontractingReceipt,
)

from inventory_tools.inventory_tools.overrides.inspection import (
	get_inspection_required,
	validate_inspection_with_company_scope,
)


class InventoryToolsSubcontractingReceipt(SubcontractingReceipt):
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

	def validate_inspection(self):
		validate_inspection_with_company_scope(self)


def handle_scr_quarantine(doc, method):
	settings = frappe.get_doc("Inventory Tools Settings", doc.company)

	if not settings.enable_quarantine_workflow:
		return

	for row in doc.items:
		if get_inspection_required(row.item_code, doc.company, "inspection_required_before_purchase"):
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
