# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

"""Quality Inspection: use company-scoped Item Default for inspection_required checks."""

import frappe
from frappe import _
from frappe.utils import get_link_to_form

from erpnext.stock.doctype.quality_inspection.quality_inspection import QualityInspection

from inventory_tools.inventory_tools.overrides.inspection import get_inspection_required

REFERENCE_TO_FIELD = {
	"Purchase Receipt": "inspection_required_before_purchase",
	"Purchase Invoice": "inspection_required_before_purchase",
	"Subcontracting Receipt": "inspection_required_before_purchase",
	"Delivery Note": "inspection_required_before_delivery",
	"Sales Invoice": "inspection_required_before_delivery",
}


class InventoryToolsQualityInspection(QualityInspection):
	def validate_inspection_required(self):
		"""Use Item Default (company-scoped) instead of Item-level inspection fields."""
		if frappe.db.get_single_value(
			"Stock Settings", "allow_to_make_quality_inspection_after_purchase_or_delivery"
		):
			return

		field_name = REFERENCE_TO_FIELD.get(self.reference_type)
		if not field_name:
			return

		company = None
		if self.reference_type and self.reference_name:
			company = frappe.get_cached_value(self.reference_type, self.reference_name, "company")
		if not company:
			return

		if not get_inspection_required(self.item_code, company, field_name):
			label = (
				"Inspection Required before Purchase"
				if "purchase" in field_name
				else "Inspection Required before Delivery"
			)
			frappe.throw(
				_("'{0}' has disabled for the item {1}, no need to create the QI").format(
					label, get_link_to_form("Item", self.item_code)
				)
			)
