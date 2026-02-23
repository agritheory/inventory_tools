# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

"""Company-scoped quality inspection requirements via Item Default."""

import frappe


INSPECTION_FIELDNAMES = (
	"inspection_required_before_purchase",
	"inspection_required_before_delivery",
	"inspection_required_before_manufacture",
)

INSPECTION_FIELDNAME_MAP = {
	"Purchase Receipt": "inspection_required_before_purchase",
	"Purchase Invoice": "inspection_required_before_purchase",
	"Subcontracting Receipt": "inspection_required_before_purchase",
	"Sales Invoice": "inspection_required_before_delivery",
	"Delivery Note": "inspection_required_before_delivery",
	"Stock Entry": "inspection_required_before_manufacture",
}


def get_inspection_required(item_code: str, company: str, field_name: str) -> bool:
	"""
	Check if inspection is required for an item in a given company context.

	Uses Item Default only; inspection fields exist at Item Default level, not Item.
	"""
	if field_name not in INSPECTION_FIELDNAMES:
		return False

	item_default_val = frappe.db.get_value(
		"Item Default",
		{"parent": item_code, "company": company},
		field_name,
	)
	return bool(item_default_val) if item_default_val is not None else False


def validate_inspection_with_company_scope(doc) -> None:
	"""
	Validate quality inspection using company-scoped Item Default overrides.

	Replicates StockController.validate_inspection but uses get_inspection_required
	so QC requirements can vary by company (e.g. bakery vs fruit wholesaler).

	Calls doc.validate_qi_presence/submission/rejection so overrides (e.g. quarantine
	bypass) are preserved.
	"""
	inspection_required_fieldname = INSPECTION_FIELDNAME_MAP.get(doc.doctype)

	# Return if inspection is not required on document level
	if (
		(not inspection_required_fieldname and doc.doctype != "Stock Entry")
		or (
			doc.doctype == "Stock Entry"
			and not getattr(doc, "inspection_required", False)
			and not _has_item_with_manufacture_inspection(doc)
		)
		or (
			doc.doctype in ["Sales Invoice", "Purchase Invoice"] and not getattr(doc, "update_stock", False)
		)
	):
		return

	for row in doc.get("items") or []:
		qi_required = False
		if inspection_required_fieldname and get_inspection_required(
			row.item_code, doc.company, inspection_required_fieldname
		):
			qi_required = True
		elif doc.doctype == "Stock Entry" and row.get("t_warehouse"):
			qi_required = getattr(doc, "inspection_required", False) or get_inspection_required(
				row.item_code, doc.company, "inspection_required_before_manufacture"
			)

		if row.get("is_scrap_item"):
			continue

		if qi_required:
			doc.validate_qi_presence(row)
			if doc.docstatus == 1:
				doc.validate_qi_submission(row)
				doc.validate_qi_rejection(row)


def _has_item_with_manufacture_inspection(doc) -> bool:
	"""Check if any item in doc requires manufacture inspection (for Stock Entry early-exit)."""
	for row in doc.get("items") or []:
		if row.get("t_warehouse") and get_inspection_required(
			row.item_code, doc.company, "inspection_required_before_manufacture"
		):
			return True
	return False
