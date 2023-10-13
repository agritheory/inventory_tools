# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt
from itertools import groupby

import frappe
from frappe.query_builder import DocType


def execute(filters=None):
	SalesOrder = DocType("Sales Order")
	SalesOrderItem = DocType("Sales Order Item")
	query = (
		frappe.qb.from_(SalesOrder)
		.join(SalesOrderItem)
		.on(SalesOrder.name == SalesOrderItem.parent)
		.select(
			SalesOrder.name.as_("sales_order"),
			SalesOrderItem.item_code,
			SalesOrderItem.warehouse,
			SalesOrderItem.delivery_date,
			SalesOrderItem.qty.as_("so_qty"),
		)
		.where(SalesOrder.docstatus == 1)
		.where(SalesOrder.company == filters.company)
	)

	if filters.customer:
		query = query.where(SalesOrder.customer == filters.customer)
	if filters.delivery_date_start:
		query = query.where(SalesOrderItem.delivery_date >= filters.delivery_date_start)
	if filters.delivery_date_end:
		query = query.where(SalesOrderItem.delivery_date <= filters.delivery_date_end)
	if filters.warehouse:
		query = query.where(SalesOrderItem.warehouse.isin(filters.warehouse))

	data = query.run(as_dict=1)

	output = []

	for sales_order, _rows in groupby(data, lambda x: x.get("sales_order")):
		output.append({"sales_order": sales_order, "indent": 0, "picked_percentage": "100"})
		for row in _rows:
			del row["sales_order"]
			output.append({**row, "indent": 1})

	return get_columns(), output


def get_columns():
	return [
		{
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"label": "Sales Order",
			"width": "200px",
		},
		{
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"label": "Item",
			"width": "250px",
		},
		{
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"label": "Warehouse",
			"width": "250px",
		},
		{
			"fieldname": "so_qty",
			"label": "SO Qty",
			"fieldtype": "Data",
		},
		{
			"fieldname": "delivery_date",
			"label": "Delivery Date",
			"fieldtype": "Date",
			"width": "120px",
		},
		{
			"fieldname": "picked_percentage",
			"label": "% Picked",
			"fieldtype": "Data",
			"width": "100px",
		},
		{
			"fieldname": "total_stock",
			"fieldtype": "Data",
			"label": "Total Stock",
			"width": "120px",
		},
	]
