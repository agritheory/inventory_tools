# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

from itertools import groupby

import frappe
from frappe.query_builder import DocType


def execute(filters=None):
	if (filters.start_date and filters.end_date) and (filters.start_date > filters.end_date):
		frappe.throw(frappe._("Start date cannot be before end date"))
	return get_columns(filters), get_data(filters)


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
		.where(Quotation.transaction_date[filters.start_date : filters.end_date])
		.orderby(Quotation.party_name, QuotationItem.item_name)
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


def get_columns(filters):
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
