# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import json
from itertools import groupby

import frappe
from frappe.query_builder import DocType


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
			Quotation.party_name.as_("customer"),
			Quotation.transaction_date,
			QuotationItem.item_code,
			QuotationItem.item_name,
			QuotationItem.qty,
			QuotationItem.uom,
			QuotationItem.warehouse,
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
			r["split_qty"] = r["qty"]
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
			"width": "200px",
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
			"width": "120px",
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
			"label": "Qty",
			"fieldname": "qty",
			"fieldtype": "Data",
			"width": "90px",
			"align": "right",
		},
		{
			"label": "Split Qty",
			"fieldname": "split_qty",
			"fieldtype": "Data",
			"width": "90px",
			"align": "right",
		},
		{"fieldname": "currency", "fieldtype": "Link", "options": "Currency", "hidden": 1},
	]


@frappe.whitelist()
def create(company, warehouse, filters, rows):
	filters = frappe._dict(json.loads(filters)) if isinstance(filters, str) else filters
	rows = json.loads(rows) if isinstance(rows, str) else rows
	if not rows:
		return

	counter = 0

	for customer, _rows in groupby(rows, lambda x: x.get("customer")):
		rows = list(_rows)

		if company:
			print("PASA")
			so = frappe.new_doc("Sales Order")
			so.transaction_date = rows[0].get("transaction_date")
			so.customer = customer
			so.company = company

			for row in rows:
				if not row.get("item_code"):
					continue

				so.append(
					"items",
					{
						"item_code": row.get("item_code"),
						"item_name": row.get("item_name"),
						"delivery_date": row.get("transaction_date"),
						"uom": row.get("uom"),
						"qty": row.get("split_qty"),
						"warehouse": warehouse,
						"quotation_item": row.get("quotation_item"),
						"prevdoc_docname": row.get("quotation"),
					},
				)
			so.multi_company_sales_order = True
			so.save()
			counter += 1
		else:
			for quotation_company, _company_rows in groupby(rows, lambda x: x.get("company")):
				rows = list(_company_rows)
				so = frappe.new_doc("Sales Order")
				so.transaction_date = rows[0].get("transaction_date")
				so.customer = customer
				so.company = quotation_company

				for row in rows:
					if not row.get("item_code"):
						continue

					so.append(
						"items",
						{
							"item_code": row.get("item_code"),
							"item_name": row.get("item_name"),
							"delivery_date": row.get("transaction_date"),
							"uom": row.get("uom"),
							"qty": row.get("split_qty"),
							"warehouse": row.get("warehouse"),
							"quotation_item": row.get("quotation_item"),
							"prevdoc_docname": row.get("quotation"),
						},
					)
				so.save()
				counter += 1

	frappe.msgprint(frappe._(f"{counter} Sales Orders created"), alert=True, indicator="green")
