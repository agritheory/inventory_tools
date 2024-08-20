# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.desk.reportview import execute


@frappe.whitelist()
def uom_restricted_query(doctype, txt, searchfield, start, page_len, filters):
	if "company" in filters:
		company = filters.pop("company")
	else:
		company = frappe.defaults.get_defaults().get("company")

	if frappe.get_cached_value("Inventory Tools Settings", company, "enforce_uoms"):
		return frappe.get_all(
			"UOM Conversion Detail",
			filters=filters,
			fields=["uom", "conversion_factor"],
			limit_start=start,
			limit_page_length=page_len,
			as_list=True,
		)
	if "parent" in filters:
		filters.pop("parent")
	return execute(
		"UOM",
		filters=filters,
		fields=[searchfield],
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,
	)


@frappe.whitelist()
def validate_uom_has_conversion(doc, method=None):
	company = doc.company if doc.get("company") else frappe.defaults.get_defaults().get("company")
	if not frappe.get_cached_value("Inventory Tools Settings", company, "enforce_uoms"):
		return
	uom_enforcement = get_uom_enforcement()
	if doc.doctype not in uom_enforcement:
		return
	invalid_data = []
	for form_doctype, config in uom_enforcement.get(doc.doctype).items():
		if doc.doctype == form_doctype:
			for field in config:
				invalid_data.append(validate_uom_conversion(doc, field))
		else:
			for child_table_field, fields in config.items():
				for row in doc.get(child_table_field):
					for field in fields:
						invalid_data.append(validate_uom_conversion(row, field))

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


@frappe.whitelist()
def get_uom_enforcement():
	return frappe.get_hooks("inventory_tools_uom_enforcement")
