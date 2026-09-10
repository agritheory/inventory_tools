# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

TEMPLATE_DOCTYPE = "Shipment Parcel Template"
INTERIOR_UOM = "Centimeter"


def sync_shipment_parcel_template_interior(doc, method=None):
	"""Create or update Interior Physical Dimension from Shipment Parcel Template fields."""
	if not frappe.db.exists("DocType", TEMPLATE_DOCTYPE):
		return

	if not is_parcel_template_physical_dimension_sync_enabled():
		return

	existing = frappe.db.get_value(
		"Physical Dimension",
		{
			"reference_doctype": TEMPLATE_DOCTYPE,
			"reference_document": doc.name,
			"dimension_type": "Interior",
			"uom": INTERIOR_UOM,
		},
		"name",
	)

	if existing:
		pd = frappe.get_doc("Physical Dimension", existing)
	else:
		pd = frappe.new_doc("Physical Dimension")
		pd.reference_doctype = TEMPLATE_DOCTYPE
		pd.reference_document = doc.name
		pd.dimension_type = "Interior"
		pd.uom = INTERIOR_UOM

	pd.item_length = flt(doc.length)
	pd.item_width = flt(doc.width)
	pd.item_height = flt(doc.height)
	pd.item_weight = flt(doc.weight)

	if existing:
		pd.save(ignore_permissions=True)
	else:
		pd.insert(ignore_permissions=True)


def is_parcel_template_physical_dimension_sync_enabled():
	return bool(
		frappe.db.get_value(
			"Inventory Tools Settings",
			{"sync_parcel_template_physical_dimension": 1},
			"name",
		)
	)
