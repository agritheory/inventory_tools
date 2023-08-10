# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.desk.reportview import execute
from frappe.desk.search import search_link


@frappe.whitelist()
def uom_restricted_query(doctype, txt, searchfield, start, page_len, filters):
	company = frappe.defaults.get_defaults().get("company")
	if frappe.get_cached_value("Inventory Tools", company, "enforce_uoms"):
		return execute(
			"UOM Conversion Detail",
			filters=filters,
			fields=["uom"],
			limit_start=start,
			limit_page_length=page_len,
			as_list=True,
		)
	return search_link(doctype, txt, searchfield, start, page_len, filters)


@frappe.whitelist()
def validate_uom_has_conversion(doc, method=None):
	company = doc.company if doc.company else frappe.defaults.get_defaults().get("company")
	if not frappe.get_cached_value("Inventory Tools", company, "enforce_uoms"):
		return
	# TODO: make UOM enforcement doctypes and fields hookable
	# _uom_enforcement = frappe.get_hooks()
	if doc.doctype not in uom_enforcement:
		return
	invalid_data = []
	for field in uom_enforcement.get(doc.doctype):
		if "." in field:
			table = field.split(".")[0]
			field = field.split(".")[1]
			for row in doc.get(table):
				invalid_data.append(validate_uom_conversion(row, field))
		else:
			invalid_data.append(validate_uom_conversion(doc, field))

	if not any(invalid_data):
		return

	error_msg = '<table class="table table-hover"><tbody>'
	error_msg += (
		"<tr><th>"
		+ frappe._("Row")
		+ "</th><th>"
		+ frappe._("Item")
		+ "</th><th>"
		+ frappe._("Invalid UOM")
		+ "</th><th>"
		+ frappe._("Valid UOMs")
		+ "</th></tr>"
	)
	for row in invalid_data:
		if not row:
			continue
		error_msg += f"<tr><td> {row.index} </td><td> {row.item_code}:{row.item_name}</td><td> {row.invalid_uom} </td><td> {row.valid_uoms} </td></tr>"
	error_msg += "</tbody></table>"
	frappe.msgprint(
		title=frappe._("This Document contains invalid UOMs"),
		msg=error_msg,
		indicator="red",
		raise_exception=True,
	)


def validate_uom_conversion(doc, field):
	if not doc.get(field):
		return
	if doc.doctype == "Item":
		valid_uoms = [u.get("uom") for u in doc.uoms]
	else:
		valid_uoms = [
			u["uom"]
			for u in frappe.get_all("UOM Conversion Detail", {"parent": doc.get("item_code")}, "uom")
		]
	if not valid_uoms:
		return
	item_name = doc.item_code
	if hasattr(doc, "item_name"):
		item_name = doc.item_name
	if doc.get(field) not in valid_uoms:
		return frappe._dict(
			{
				"index": f"{frappe._('Row')} {doc.idx}" if doc.idx else doc.name,
				"item_code": doc.item_code,
				"item_name": item_name,
				"valid_uoms": (", ").join(valid_uoms),
				"invalid_uom": doc.get(field),
			}
		)


@frappe.whitelist()
def duplicate_weight_to_uom_conversion(doc, method=None):
	if not (doc.weight_per_unit and doc.weight_uom):
		return
	if len(list(filter(lambda x: x.uom == doc.weight_uom, doc.uoms))) == 1:
		return

	doc.append(
		"uoms",
		{
			"uom": doc.weight_uom,
			"conversion_factor": doc.weight_per_unit,
		},
	)


uom_enforcement = {
	"BOM": [
		"items.uom",
	],
	"Delivery Note": [
		"items.uom",
		"items.weight_uom",
	],
	"Item Price": [
		"uom",
	],
	"Item": [
		"sales_uom",
		"purchase_uom",
		"weight_uom",
		"barcodes.uom",
	],
	"Job Card": ["items.uom", "items.stock_uom"],
	"Material Request": [
		"items.uom",
	],
	"Opportunity": [
		"items.uom",
	],
	"Pick List": [
		"locations.uom",
	],
	"POS Invoice": [
		"items.uom",
	],
	"Production Plan": [
		"po_items.planned_uom",
	],
	"Purchase Invoice": [
		"items.uom",
		"items.weight_uom",
	],
	"Purchase Order": [
		"items.uom",
	],
	"Purchase Receipt": [
		"items.uom",
		"items.weight_uom",
	],
	"Putaway Rule": [
		"uom",
	],
	"Quotation": [
		"items.uom",
	],
	"Request for Quotation": [
		"items.uom",
	],
	"Sales Invoice": [
		"items.uom",
	],
	"Sales Order": [
		"items.uom",
		"items.weight_uom",
	],
	"Stock Entry": [
		"items.uom",
	],
	"Supplier Quotation": [
		"items.uom",
	],
}
