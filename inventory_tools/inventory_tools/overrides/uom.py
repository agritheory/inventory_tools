# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import frappe


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
