# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt
import json
from itertools import groupby

import frappe
from erpnext.stock.doctype.pick_list.pick_list import get_available_item_locations
from frappe.query_builder import DocType
from frappe.utils.nestedset import get_descendants_of


def execute(filters=None):
	return get_columns(), get_report_output(filters)


def get_report_output(filters=None, ignore_validation=True):
	SalesOrder = DocType("Sales Order")
	SalesOrderItem = DocType("Sales Order Item")
	query = (
		frappe.qb.from_(SalesOrder)
		.join(SalesOrderItem)
		.on(SalesOrder.name == SalesOrderItem.parent)
		.select(
			SalesOrder.name.as_("sales_order"),
			SalesOrder.per_picked,
			SalesOrderItem.item_code,
			SalesOrderItem.warehouse,
			SalesOrderItem.delivery_date,
			SalesOrderItem.qty.as_("so_qty"),
		)
		.where(SalesOrder.docstatus == 1)
		.where(SalesOrder.company == filters.company)
	)

	if filters.status:
		if filters.status == "Already Picked":
			query = query.where(SalesOrder.per_picked == 100)
		elif filters.status == "Not Picked":
			query = query.where(SalesOrder.per_picked < 100)
		elif filters.status == "Unshipped":
			query = query.where(SalesOrder.per_delivered < 100)
	if filters.customer:
		query = query.where(SalesOrder.customer == filters.customer)
	if filters.delivery_date_start:
		query = query.where(SalesOrderItem.delivery_date >= filters.delivery_date_start)
	if filters.delivery_date_end:
		query = query.where(SalesOrderItem.delivery_date <= filters.delivery_date_end)
	if filters.warehouse:
		from_warehouses = get_descendants_of("Warehouse", filters.warehouse)
	else:
		from_warehouses = frappe.get_all("Warehouse", pluck="name")

	query = query.where(SalesOrderItem.warehouse.isin(from_warehouses))
	data = query.run(as_dict=1)
	output = []

	for sales_order, _rows in groupby(data, lambda x: x.get("sales_order")):
		rows = list(_rows)
		output.append(
			{"sales_order": sales_order, "indent": 0, "per_picked": f'{rows[0]["per_picked"]} %'}
		)
		for row in rows:
			del row["sales_order"]
			del row["per_picked"]
			qty_available = get_available_item_locations(
				row["item_code"],
				from_warehouses,
				row["so_qty"],
				filters.company,
				ignore_validation=ignore_validation,
				picked_item_details=None,
			)
			row["total_stock"] = "Total Availability" if qty_available else "Not Total Availability"
			output.append({**row, "indent": 1})

	return output


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
			"fieldname": "per_picked",
			"label": "% Picked",
			"fieldtype": "Data",
			"width": "100px",
		},
		{
			"fieldname": "total_stock",
			"fieldtype": "Data",
			"label": "Total Stock",
			"width": "150px",
		},
	]


@frappe.whitelist()
def check_stock(filters):
	filters = frappe._dict(json.loads(filters)) if isinstance(filters, str) else filters
	get_report_output(filters=filters, ignore_validation=False)
