# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import json
from itertools import groupby

import frappe
from frappe.query_builder import DocType
from frappe.utils.data import fmt_money


def execute(filters=None):
	if (filters.start_date and filters.end_date) and (filters.start_date > filters.end_date):
		frappe.throw(frappe._("Start date cannot be before end date"))
	return get_columns(), get_data(filters)


def get_data(filters):
	Quotation = DocType("Quotation")
	QuotationItem = DocType("Quotation Item")
	query = (
		frappe.qb.from_(Quotation)
		.inner_join(QuotationItem)
		.on(Quotation.name == QuotationItem.parent)
		.select(
			QuotationItem.name.as_("quotation_item"),
			Quotation.name.as_("quotation"),
			Quotation.company,
			Quotation.currency,
			Quotation.party_name.as_("customer"),
			Quotation.transaction_date,
			QuotationItem.item_code,
			QuotationItem.item_name,
			QuotationItem.qty,
			QuotationItem.uom,
			QuotationItem.warehouse,
			QuotationItem.rate,
		)
		.where(Quotation.docstatus < 2)
		.where(Quotation.quotation_to == "Customer")
		.where(
			Quotation.transaction_date[filters.start_date or "1900-01-01" : filters.en_date or "2100-12-31"]
		)
		.orderby(Quotation.party_name, Quotation.name, QuotationItem.item_name)
	)

	if filters.company:
		query = query.where(Quotation.company == filters.company)

	data = query.run(as_dict=1)

	output = []
	for customer, _rows in groupby(data, lambda x: x.get("customer")):
		rows = list(_rows)
		output.append({"customer": customer, "indent": 0})
		for r in rows:
			r.split_qty = r["qty"]
			r.price = fmt_money(r.get("rate"), 2, r.get("currency")).replace(" ", "")
			r.draft_so = frappe.db.get_value(
				"Sales Order Item",
				{"quotation_item": r.quotation_item, "docstatus": 0},
				"sum(qty) as qty",
			)
			r.draft_so = f'<span style="color: red">{r.draft_so}</span>' if r.draft_so else None
			output.append({**r, "indent": 1})
	return output


def get_columns():
	hide_company = True if len(frappe.get_all("Company")) == 1 else False
	return [
		{
			"label": "Customer",
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": "250px",
		},
		{
			"fieldname": "quotation",
			"fieldtype": "Link",
			"options": "Quotation",
			"label": "Quotation",
			"width": "170px",
		},
		{
			"fieldname": "company",
			"label": "Company",
			"fieldtype": "Data",
			"width": "200px",
			"hidden": hide_company,
		},
		{
			"fieldname": "transaction_date",
			"label": "Date",
			"fieldtype": "Date",
			"width": "100px",
		},
		{
			"fieldname": "quotation_item",
			"fieldtype": "Data",
			"hidden": 1,
		},
		{
			"fieldname": "warehouse",
			"label": "Warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": "200px",
		},
		{
			"fieldname": "item_code",
			"label": "Item",
			"fieldtype": "Link",
			"options": "Item",
			"width": "250px",
		},
		{"fieldname": "item_name", "fieldtype": "Data", "hidden": 1},
		{
			"label": "Draft SOs",
			"fieldname": "draft_so",
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
			"label": "Qty",
			"fieldname": "qty",
			"fieldtype": "Data",
			"width": "50px",
			"align": "right",
		},
		{
			"label": "Split Qty",
			"fieldname": "split_qty",
			"fieldtype": "Data",
			"width": "70px",
			"align": "right",
		},
		{"fieldname": "currency", "fieldtype": "Link", "options": "Currency", "hidden": 1},
		{
			"label": "Price",
			"fieldname": "price",
			"fieldtype": "Data",
			"width": "90px",
			"align": "right",
		},
		{"fieldname": "rate", "fieldtype": "Data", "hidden": 1},
	]


@frappe.whitelist()
def create(company, filters, rows):
	filters = frappe._dict(json.loads(filters)) if isinstance(filters, str) else filters
	rows = [frappe._dict(r) for r in json.loads(rows)] if isinstance(rows, str) else rows
	if not rows:
		return
	counter = 0
	settings = frappe.get_doc("Inventory Tools Settings", company)
	requesting_companies = list({row.company for row in rows})
	if settings.sales_order_aggregation_company == company:
		requesting_companies = [company]

	for requesting_company in requesting_companies:
		for customer, _rows in groupby(rows, lambda x: x.get("customer")):
			rows = list(_rows)
			so = frappe.new_doc("Sales Order")
			so.transaction_date = rows[0].get("transaction_date")
			so.customer = customer
			if settings.sales_order_aggregation_company and len(requesting_companies) == 1:
				so.multi_company_sales_order = True
				so.company = settings.sales_order_aggregation_company
			else:
				so.company = requesting_company
			for row in rows:
				if not row.get("item_code"):
					continue

				if settings.sales_order_aggregation_company == so.company or so.company == row.company:
					if (
						settings.sales_order_aggregation_company == so.company
						and settings.aggregated_sales_warehouse
					):
						warehouse = settings.aggregated_sales_warehouse
					else:
						warehouse = frappe.get_value("Quotation Item", row.quotation_item, "warehouse")

					so.append(
						"items",
						{
							"item_code": row.get("item_code"),
							"item_name": row.get("item_name"),
							"delivery_date": row.get("transaction_date"),
							"uom": row.get("uom"),
							"qty": row.get("split_qty"),
							"rate": row.get("rate"),
							"warehouse": warehouse,
							"quotation_item": row.get("quotation_item"),
							"prevdoc_docname": row.get("quotation"),
						},
					)

			if so.items:
				so.save()
				counter += 1

	frappe.msgprint(frappe._(f"{counter} Sales Orders created"), alert=True, indicator="green")
