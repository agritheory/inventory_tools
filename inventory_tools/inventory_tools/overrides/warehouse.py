# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.desk.reportview import get_filters_cond, get_match_cond
from frappe.desk.search import search_link


@frappe.whitelist()
def update_warehouse_path(doc, method=None) -> None:
	if not frappe.db.exists("Inventory Tools Settings", doc.company):
		return
	warehouse_path = frappe.db.get_value(
		"Inventory Tools Settings", doc.company, "update_warehouse_path"
	)
	if not warehouse_path:
		return

	def get_parents(doc):
		parents = [doc.warehouse_name]
		parent = doc.parent_warehouse
		while parent:
			parent_name = frappe.get_value("Warehouse", parent, "warehouse_name")
			if parent_name != "All Warehouses":
				parents.append(parent_name)
				parent = frappe.get_value("Warehouse", parent, "parent_warehouse")
			else:
				break
		return parents

	def _update_warehouse_path(doc):
		parents = get_parents(doc)
		if parents:
			if len(parents) > 1:
				if parents[1] in parents[0]:
					parents[0] = parents[0].replace(parents[1], "")
					parents[0] = parents[0].replace(" - ", "")
			return " \u21D2 ".join(parents[::-1])
		else:
			return ""

	doc.warehouse_path = _update_warehouse_path(doc)


@frappe.whitelist()
def warehouse_query(doctype, txt, searchfield, start, page_len, filters):
	company = frappe.defaults.get_defaults().get("company")
	if not company:
		return search_link(doctype, txt, searchfield, start, page_len, filters)
	if not frappe.db.exists("Inventory Tools Settings", company) and frappe.db.get_value(
		"Inventory Tools Settings", company, "update_warehouse_path"
	):
		return search_link(doctype, txt, searchfield, start, page_len, filters)
	else:
		doctype = "Warehouse"
		conditions = []
		searchfields = frappe.get_meta(doctype).get_search_fields()
		searchfields.remove("name")
		searchfields = ["name"] + searchfields

		return frappe.db.sql(
			f"""SELECT {', '.join(searchfields)}
			FROM `tabWarehouse`
			WHERE `tabWarehouse`.`{searchfield}` like %(txt)s
				{get_filters_cond(doctype, filters, conditions).replace("%", "%%")}
				{get_match_cond(doctype).replace("%", "%%")}
			ORDER BY
				IF(LOCATE(%(_txt)s, name), LOCATE(%(_txt)s, name), 99999),
				idx DESC, name
			LIMIT %(start)s, %(page_len)s""",
			{
				"txt": "%" + txt + "%",
				"_txt": txt.replace("%", ""),
				"start": start or 0,
				"page_len": page_len or 20,
			},
		)
