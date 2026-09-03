# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import flt, getdate

from inventory_tools.inventory_tools.report.quotation_demand.quotation_demand import (
	execute as execute_quotation_demand,
)


@pytest.mark.order(7)
def test_report_without_aggregation():
	filters = frappe._dict({"end_date": getdate()})
	columns, rows = execute_quotation_demand(filters)
	assert len(rows) == 10
	assert rows[1].get("customer") == "Almacs Food Group"

	selected_rows = [
		row for row in rows if row.get("customer") == "Almacs Food Group" and row.get("company")
	]

	frappe.call(
		"inventory_tools.inventory_tools.report.quotation_demand.quotation_demand.create",
		**{
			"company": "Ambrosia Pie Company",
			"filters": filters,
			"rows": frappe.as_json(selected_rows),
		},
	)

	sos = [
		frappe.get_doc("Sales Order", so)
		for so in frappe.get_all("Sales Order", {"docstatus": 0}, pluck="name")
	]
	assert "Donwtown Deli" not in [so.get("customer") for so in sos]
	assert len(sos) == 2
	assert len(list(filter(lambda d: d.company == "Chelsea Fruit Co", sos))) == 1
	assert len(list(filter(lambda d: d.company == "Ambrosia Pie Company", sos))) == 1
	for so in sos:
		if so.company == "Almacs Food Group":
			assert so.grand_total == flt(144.84, 2)
		elif so.company == "Chelsea Fruit Co":
			assert so.grand_total == flt(160.00, 2)

		for item in so.items:
			quotation_wh = frappe.get_value("Quotation Item", item.quotation_item, "warehouse")
			assert item.warehouse == quotation_wh
		frappe.delete_doc("Sales Order", so.name)


@pytest.mark.order(8)
def test_report_with_aggregation_and_no_aggregation_warehouse():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.sales_order_aggregation_company = settings.name
	settings.aggregated_sales_warehouse = None
	settings.update_warehouse_path = True
	settings.save()

	filters = frappe._dict({"end_date": getdate()})
	columns, rows = execute_quotation_demand(filters)
	assert len(rows) == 10
	assert rows[1].get("customer") == "Almacs Food Group"

	selected_rows = [
		row for row in rows if row.get("customer") == "Almacs Food Group" and row.get("company")
	]

	frappe.call(
		"inventory_tools.inventory_tools.report.quotation_demand.quotation_demand.create",
		**{
			"company": "Chelsea Fruit Co",
			"filters": filters,
			"rows": frappe.as_json(selected_rows),
		},
	)

	sos = [
		frappe.get_doc("Sales Order", so)
		for so in frappe.get_all("Sales Order", {"docstatus": 0}, pluck="name")
	]
	assert len(sos) == 1
	so = sos[0]
	assert so.customer == "Almacs Food Group"
	assert so.company == "Chelsea Fruit Co"
	assert so.grand_total == flt(304.84, 2)
	for item in so.items:
		quotation_wh = frappe.get_value("Quotation Item", item.quotation_item, "warehouse")
		assert item.warehouse == quotation_wh
	frappe.delete_doc("Sales Order", so.name)


@pytest.mark.order(9)
def test_report_with_aggregation_and_aggregation_warehouse():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.sales_order_aggregation_company = settings.name
	settings.aggregated_sales_warehouse = "Shipping - CFC"
	settings.update_warehouse_path = True
	settings.save()

	filters = frappe._dict({"end_date": getdate()})
	columns, rows = execute_quotation_demand(filters)
	assert len(rows) == 10
	assert rows[1].get("customer") == "Almacs Food Group"

	selected_rows = [
		row for row in rows if row.get("customer") == "Almacs Food Group" and row.get("company")
	]

	frappe.call(
		"inventory_tools.inventory_tools.report.quotation_demand.quotation_demand.create",
		**{
			"company": "Chelsea Fruit Co",
			"filters": filters,
			"rows": frappe.as_json(selected_rows),
		},
	)

	sos = [
		frappe.get_doc("Sales Order", so)
		for so in frappe.get_all("Sales Order", {"docstatus": 0}, pluck="name")
	]
	assert len(sos) == 1
	so = sos[0]
	assert so.customer == "Almacs Food Group"
	assert so.company == "Chelsea Fruit Co"
	assert so.grand_total == flt(304.84, 2)
	for item in so.items:
		assert item.warehouse == "Shipping - CFC"
	frappe.delete_doc("Sales Order", so.name)


@pytest.mark.order(39)
def test_chelsea_fruit_sales_order_uses_standard_selling_prices():
	"""Whole Harvest fruit order on Chelsea Fruit Co must not price Bayberry, Kepel, and Lychee at zero."""
	so_name = frappe.db.get_value(
		"Sales Order",
		{
			"customer": "Whole Harvest Grocery Group",
			"company": "Chelsea Fruit Co",
			"docstatus": 1,
		},
	)
	assert so_name, "Setup should create the Chelsea Fruit Co sales order for Whole Harvest"
	so = frappe.get_doc("Sales Order", so_name)
	assert so.selling_price_list == "Standard Selling"
	assert so.grand_total > 0
	expected_list_rate = {"Bayberry": 0.45, "Kepel": 0.93, "Lychee": 0.21}
	assert {item.item_code for item in so.items} == set(expected_list_rate)
	for item in so.items:
		assert item.price_list_rate == expected_list_rate[item.item_code]
		assert item.rate > 0
