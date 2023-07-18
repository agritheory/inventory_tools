# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import json
from itertools import groupby

import frappe
from erpnext.stock.doctype.item.item import get_last_purchase_details
from erpnext.stock.get_item_details import get_price_list_rate_for
from frappe.utils.data import fmt_money, getdate


def execute(filters=None):
	if (filters.start_date and filters.end_date) and (filters.start_date > filters.end_date):
		frappe.throw(frappe._("Start date cannot be before end date"))

	return get_columns(filters), get_data(filters)


def get_columns(filters):
	file_export = True if frappe.form_dict.cmd == "frappe.desk.query_report.export_query" else False
	hide_company = True if len(frappe.get_all("Company")) == 1 else False
	return [
		{
			"label": "Supplier",
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": "250px",
		},
		{
			"fieldname": "material_request",
			"fieldtype": "Link",
			"options": "Material Request",
			"label": "Material Request",
			"width": "200px",
		},
		{
			"fieldname": "company",
			"label": "Company",
			"fieldtype": "Data",
			"width": "120px",
			"hidden": hide_company,
		},
		{
			"fieldname": "schedule_date",
			"label": "Required By",
			"fieldtype": "Date",
			"width": "120px",
		},
		{
			"fieldname": "material_request_item",
			"fieldtype": "Data",
			"hidden": 1,
		},
		{
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"hidden": 1,
		},
		{
			"fieldname": "item_code",
			"label": "Item",
			"fieldtype": "Link",
			"options": "Item",
			"width": "250px",
		},
		{"fieldname": "item_name", "fieldtype": "Data", "hidden": 1},  # unset for export
		{
			"label": "MR Qty",
			"fieldname": "qty",
			"fieldtype": "Data",
			"width": "90px",
			"align": "right",
		},
		{
			"label": "Total Demand",
			"fieldname": "total_demand",
			"fieldtype": "Data",
			"width": "90px",
			"align": "right",
		},
		{
			"label": "Total Selected",
			"fieldname": "total_selected",
			"fieldtype": "Data",
			"width": "90px",
			"align": "right",
		},
		{
			"label": "UOM",
			"fieldname": "uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": "90px",
		},
		{
			"label": "Price",
			"fieldname": "supplier_price",
			"fieldtype": "Data",
			"width": "90px",
			"align": "right",
		},
		{
			"label": "Selected Amount",
			"fieldname": "amount",
			"fieldtype": "Data",
			"width": "120px",
			"align": "right",
		},
		{"fieldname": "currency", "fieldtype": "Link", "options": "Currency", "hidden": 1},
	]


def get_data(filters):
	output = []
	# TODO: refactor to frappe query builder
	company_query = "AND `tabMaterial Request`.company = (%(company)s)" if filters.company else ""
	data = frappe.db.sql(
		f"""
	SELECT DISTINCT `tabMaterial Request Item`.name AS material_request_item,
	`tabMaterial Request`.name AS material_request,
	`tabMaterial Request`.company,
	`tabMaterial Request`.schedule_date,
	`tabMaterial Request Item`.name AS mri,
	`tabMaterial Request Item`.item_code,
	`tabMaterial Request Item`.item_name,
	`tabMaterial Request Item`.qty,
	`tabMaterial Request Item`.uom,
	`tabMaterial Request Item`.warehouse,
	`tabCompany`.default_currency AS currency,
	`tabMaterial Request Item`.rate AS supplier_price,
	COALESCE(`tabItem Supplier`.supplier, 'No Supplier') AS supplier
	FROM `tabCompany`, `tabMaterial Request`, `tabMaterial Request Item`, `tabItem Supplier`
	WHERE `tabMaterial Request`.name = `tabMaterial Request Item`.parent
	AND `tabMaterial Request`.company = `tabCompany`.name
	AND `tabMaterial Request`.docstatus < 2 
	AND `tabMaterial Request`.schedule_date BETWEEN %(start_date)s AND %(end_date)s
	AND `tabMaterial Request Item`.ordered_qty < `tabMaterial Request Item`.stock_qty
	AND `tabMaterial Request Item`.received_qty < `tabMaterial Request Item`.stock_qty
	AND `tabItem Supplier`.parent = `tabMaterial Request Item`.item_code
	{company_query}
	ORDER BY supplier, item_name
	""",
		{
			"company": filters.company,
			"start_date": filters.start_date or "1900-01-01",
			"end_date": filters.end_date or "2100-12-31",
		},
		as_dict=True,
		# debug=True,
	)
	total_demand = frappe._dict()
	mris = []
	for row in data:
		if row.item_code not in total_demand and row.mri not in mris:
			total_demand[row.item_code] = row.qty
			mris.append(row.mri)
		elif row.item_code in total_demand and row.mri not in mris:
			total_demand[row.item_code] += row.qty
			mris.append(row.mri)

	for supplier, _rows in groupby(data, lambda x: x.get("supplier")):
		rows = list(_rows)
		output.append({"supplier": supplier, "indent": 0})
		for r in rows:
			r.total_demand = total_demand[r.item_code]
			r.supplier_price = get_item_price(filters, r)
			r.supplier_price = fmt_money(r.get("supplier_price"), 2, r.get("currency")).replace(" ", "")
			output.append({**r, "indent": 1})
	return output


def get_item_price(filters, r):
	if filters.price_list:
		args = frappe._dict(
			{"price_list": filters.price_list, "uom": r.uom, "supplier": r.supplier, "qty": r.total_demand}
		)
		return get_price_list_rate_for(args, r.item_code)
	else:
		details = get_last_purchase_details(r.item_code, None, conversion_rate=1.0)
		return details.get("rate")


@frappe.whitelist()
def create_pos(company, rows):
	rows = json.loads(rows) if isinstance(rows, str) else rows
	if not rows:
		return
	companies = set()
	counter = 0
	for supplier, _rows in groupby(rows, lambda x: x.get("supplier")):
		rows = list(_rows)
		po = frappe.new_doc("Purchase Order")
		po.schedule_date = po.posting_date = getdate()
		po.supplier = supplier
		po.company = frappe.get_value("Material Request", rows[0].get("material_request"), "company")
		companies.add(po.company)
		settings = frappe.get_doc("Inventory Tools Settings", company)
		if settings.purchase_order_aggregation_company:
			po.company = settings.purchase_order_aggregation_company

		for row in rows:
			if not row.get("item_code"):
				continue
			po.append(
				"items",
				{
					"item_code": row.get("item_code"),
					"item_name": row.get("item_name"),
					"schedule_date": max(getdate(), getdate(row.get("schedule_date"))),
					"company": row.get("company"),
					"qty": row.get("qty"),
					"rate": row.get("supplier_price"),
					"uom": row.get("uom"),
					"material_request": row.get("material_request"),
					"material_request_item": row.get("material_request_item"),
					"warehouse": settings.aggregated_purchasing_warehouse
					if settings.aggregated_purchasing_warehouse
					else row.get("warehouse"),
				},
			)
		po.multi_company_purchase_order = True if len(list(companies)) > 1 else False
		po.save()
		counter += 1

	frappe.msgprint(frappe._(f"{counter} Purchase Orders created"), alert=True, indicator="green")
