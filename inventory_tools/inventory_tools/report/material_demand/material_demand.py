# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import json
from itertools import groupby

import frappe
from erpnext.stock.doctype.item.item import get_last_purchase_details
from erpnext.stock.get_item_details import get_price_list_rate_for
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Coalesce
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

	MaterialRequest = DocType("Material Request")
	MaterialRequestItem = DocType("Material Request Item")
	ItemSupplier = DocType("Item Supplier")
	Company = DocType("Company")
	query = (
		frappe.qb.from_(MaterialRequest)
		.join(MaterialRequestItem)
		.on(MaterialRequest.name == MaterialRequestItem.parent)
		.join(ItemSupplier)
		.on(ItemSupplier.parent == MaterialRequestItem.item_code)
		.join(Company)
		.on(MaterialRequest.company == Company.name)
		.select(
			MaterialRequestItem.name.as_("material_request_item"),
			MaterialRequest.name.as_("material_request"),
			MaterialRequest.company,
			MaterialRequest.schedule_date,
			MaterialRequestItem.name.as_("mri"),
			MaterialRequestItem.item_code,
			MaterialRequestItem.item_name,
			MaterialRequestItem.qty,
			MaterialRequestItem.uom,
			MaterialRequestItem.warehouse,
			Company.default_currency.as_("currency"),
			MaterialRequestItem.rate.as_("supplier_price"),
			Coalesce(ItemSupplier.supplier.as_("supplier"), "No Supplier").as_("supplier"),
		)
		.where(MaterialRequest.docstatus < 2)
		.where(
			MaterialRequest.schedule_date[
				filters.start_date or "1900-01-01" : filters.en_date or "2100-12-31"
			]
		)
		.where(MaterialRequestItem.ordered_qty < MaterialRequestItem.stock_qty)
		.where(MaterialRequestItem.received_qty < MaterialRequestItem.stock_qty)
		.orderby(Coalesce(ItemSupplier.supplier, "No Supplier"), MaterialRequestItem.item_name)
	)

	if filters.company:
		query = query.where(MaterialRequest.company == filters.company)

	data = query.run(as_dict=1)

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
def create(company, email_template, filters, creation_type, rows):
	if creation_type == "po":
		message = create_pos(company, filters, rows)
	elif creation_type == "rfq":
		message = create_rfqs(company, email_template, filters, rows)
	elif creation_type == "item_based":
		message = create_item_based(company, email_template, filters, rows)
	frappe.msgprint(message, alert=True, indicator="green")


@frappe.whitelist()
def create_item_based(company, email_template, filters, rows):
	filters = frappe._dict(json.loads(filters)) if isinstance(filters, str) else filters
	rows = json.loads(rows) if isinstance(rows, str) else rows
	if not rows:
		return

	rfq_rows = []
	po_rows = []
	rfqs_message = frappe._("0 Request For Quotation created")
	po_message = frappe._("0 Purchase Orders created")

	for row in rows:
		if frappe.get_value(
			"Item Supplier", {"parent": row["item_code"], "supplier": row["supplier"]}, "requires_rfq"
		):
			rfq_rows.append(row)
		else:
			po_rows.append(row)

	if po_rows:
		po_message = create_pos(company, filters, po_rows)

	if rfq_rows:
		rfqs_message = create_rfqs(company, email_template, filters, rfq_rows)

	return f"{po_message} {rfqs_message}"


@frappe.whitelist()
def create_rfqs(company, email_template, filters, rows):
	filters = frappe._dict(json.loads(filters)) if isinstance(filters, str) else filters
	rows = json.loads(rows) if isinstance(rows, str) else rows
	if not rows:
		return

	items = {}
	rfqs = []

	for row in rows:
		if not row.get("item_code"):
			continue
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

	settings = frappe.get_doc("Inventory Tools Settings", company)

	for rfq_data in rfqs:
		rfq = frappe.new_doc("Request for Quotation")
		rfq.transaction_date = getdate()
		rfq.company = company
		rfq.email_template = email_template

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

	return frappe._(f"{len(rfqs)} Request For Quotation created")


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

	return frappe._(f"{counter} Purchase Orders created")
