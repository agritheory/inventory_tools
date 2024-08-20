# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import getdate

from inventory_tools.inventory_tools.report.manufacturing_capacity.manufacturing_capacity import (
	get_total_demand,
)


@pytest.mark.order(10)
def test_total_demand():
	pocketful_bom_no = frappe.get_value(
		"BOM", {"item": "Pocketful of Bay", "is_active": 1, "is_default": 1}
	)
	tower_bom_no = frappe.get_value(
		"BOM", {"item": "Tower of Bay-bel", "is_active": 1, "is_default": 1}
	)

	assert 10 == get_total_demand(pocketful_bom_no)  # test data of 10
	assert 20 == get_total_demand(tower_bom_no)  # test data of 20

	# Create a Sales Order that hasn't generated a Work Order
	so = frappe.new_doc("Sales Order")
	so.company = frappe.defaults.get_defaults().get("company")
	so.transaction_date = getdate()
	so.customer = "TransAmerica Bank Cafeteria"
	so.order_type = "Sales"
	so.currency = "USD"
	so.selling_price_list = "Bakery Wholesale"
	so.append(
		"items",
		{
			"item_code": "Pocketful of Bay",
			"delivery_date": so.transaction_date,
			"qty": 5,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	so.append(
		"items",
		{
			"item_code": "Tower of Bay-bel",
			"delivery_date": so.transaction_date,
			"qty": 10,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	so.save()
	so.submit()
	so.reload()
	assert so.items[0].work_order_qty == 0.0
	assert so.items[1].work_order_qty == 0.0
	assert 15 == get_total_demand(pocketful_bom_no)  # test data of 10 + SO of 5
	assert 30 == get_total_demand(tower_bom_no)  # test data of 20 + SO of 10

	# Create a Material Request for Manufacture
	mr = frappe.new_doc("Material Request")
	mr.transaction_date = mr.schedule_date = getdate()
	mr.material_request_type = "Manufacture"
	mr.title = "Tower and Pocketful"
	mr.company = frappe.defaults.get_defaults().get("company")
	mr.append(
		"items",
		{
			"item_code": "Pocketful of Bay",
			"delivery_date": mr.schedule_date,
			"qty": 15,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	mr.append(
		"items",
		{
			"item_code": "Tower of Bay-bel",
			"delivery_date": mr.schedule_date,
			"qty": 5,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	mr.save()
	mr.submit()

	assert 30 == get_total_demand(pocketful_bom_no)  # test data of 10 + SO of 5 + MR of 15
	assert 35 == get_total_demand(tower_bom_no)  # test data of 20 + SO of 10 + MR of 5

	# cancel MR to test change in demand
	mr.cancel()
	assert 15 == get_total_demand(pocketful_bom_no)  # test data of 10 + SO of 5
	assert 30 == get_total_demand(tower_bom_no)  # test data of 20 + SO of 10

	# amend and stop to test "Stop" criteria
	_mr = frappe.copy_doc(mr)
	_mr.amended_from = mr.name
	_mr.save()
	_mr.submit()
	_mr.set_status(update=True, status="Stopped")

	assert _mr.status == "Stopped"
	assert 15 == get_total_demand(pocketful_bom_no)  # test data of 10 + SO of 5
	assert 30 == get_total_demand(tower_bom_no)  # test data of 20 + SO of 10
