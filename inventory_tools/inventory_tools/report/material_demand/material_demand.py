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
			"label": "Draft POs",
			"fieldname": "draft_po",
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
			r.draft_po = frappe.db.get_value(
				"Purchase Order Item",
				{"material_request_item": r.material_request_item, "docstatus": 0},
				"qty",
			)
			r.draft_po = f'<span style="color: red">{r.draft_po}</span>' if r.draft_po else None
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
def create(company, filters, creation_type, rows):
	if creation_type == "po":
		create_pos(company, filters, rows)
	elif creation_type == "rfq":
		create_rfqs(company, filters, rows)
	elif creation_type == "item_based":
		frappe.msgprint("TODO ITEM BASED", alert=True, indicator="green")


@frappe.whitelist()
def create_rfqs(company, filters, rows):
	filters = frappe._dict(json.loads(filters)) if isinstance(filters, str) else filters
	rows = json.loads(rows) if isinstance(rows, str) else rows
	if not rows:
		return

	items = {}
	rfqs = []

	for row in rows:
		if row["item_code"] not in items:
			items[row["item_code"]] = {"suppliers": [row["supplier"]], "rows": [row]}
		else:
			items[row["item_code"]]["suppliers"].append(row["supplier"])
			items[row["item_code"]]["rows"].append(row)

	for item_code, data in items.items():
		if len(rfqs) == 0:
			rfqs.append(
				{
					"suppliers": data["suppliers"],
					"items": [item_code],
					"rows": data["rows"],
				}
			)
		else:
			exists = False
			for rfq in rfqs:
				if rfq["suppliers"] == data["suppliers"]:
					exists = True
					break

			if exists:
				rfq["items"].append(item_code)
				rfq["rows"] = rfq["rows"] + data["rows"]
			else:
				rfqs.append(
					{
						"suppliers": data["suppliers"],
						"items": [item_code],
						"rows": data["rows"],
					}
				)

	for rfq_data in rfqs:
		rfq = frappe.new_doc("Request for Quotation")
		rfq.transaction_date = getdate()
		rfq.company = company
		rfq.message_for_supplier = "TODO"

		settings = frappe.get_doc("Inventory Tools Settings", company)

		for supplier in rfq_data["suppliers"]:
			rfq.append(
				"suppliers",
				{
					"supplier": supplier,
				},
			)

		for row in rfq_data["rows"]:
			if not row.get("item_code"):
				continue

			if rfq.items and list(filter(lambda i: i.item_code == row.get("item_code"), rfq.items)):
				continue

			rfq.append(
				"items",
				{
					"item_code": row.get("item_code"),
					"item_name": row.get("item_name"),
					"required_date": max(getdate(), getdate(row.get("schedule_date"))),
					"conversion_factor": frappe.get_value(
						"Material Request Item", row.get("material_request_item"), "conversion_factor"
					),
					"qty": row.get("qty"),
					"uom": row.get("uom"),
					"material_request": row.get("material_request"),
					"material_request_item": row.get("material_request_item"),
					"warehouse": settings.aggregated_purchasing_warehouse
					if settings.aggregated_purchasing_warehouse
					else row.get("warehouse"),
				},
			)
		rfq.set_missing_values()
		rfq.save()

	frappe.msgprint(
		frappe._(f"{len(rfqs)} Request For Quotation created"), alert=True, indicator="green"
	)


@frappe.whitelist()
def create_pos(company, filters, rows):
	filters = frappe._dict(json.loads(filters)) if isinstance(filters, str) else filters
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
		po.buying_price_list = filters.price_list
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
