import frappe
import pytest
from erpnext.manufacturing.doctype.work_order.work_order import (
	create_job_card,
	make_stock_entry,
	make_work_order,
)
from frappe.exceptions import ValidationError
from frappe.utils import getdate

from inventory_tools.inventory_tools.report.manufacturing_capacity.manufacturing_capacity import (
	get_total_demand,
)
from inventory_tools.tests.fixtures import customers


def test_total_demand():
	company = frappe.defaults.get_defaults().get("company")
	pocketful_item = "Pocketful of Bay"
	pocketful_bom_no = frappe.get_value(
		"BOM", {"item": pocketful_item, "is_active": 1, "is_default": 1}
	)
	tower_item = "Tower of Bay-bel"
	tower_bom_no = frappe.get_value("BOM", {"item": tower_item, "is_active": 1, "is_default": 1})

	# Create a Sales Order that hasn't generated a Work Order
	so = frappe.new_doc("Sales Order")
	so.transaction_date = getdate()
	so.customer = customers[-1]
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

	# Create a Material Request for Manufacture
	mr = frappe.new_doc("Material Request")
	mr.transaction_date = mr.schedule_date = getdate()
	mr.material_request_type == "Manufacture"
	mr.title = "Tower and Pocketful"
	mr.company = company
	mr.append(
		"items",
		{
			"item_code": pocketful_item,
			"delivery_date": mr.schedule_date,
			"qty": 15,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	mr.append(
		"items",
		{
			"item_code": tower_item,
			"delivery_date": mr.schedule_date,
			"qty": 5,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	mr.save()
	mr.submit()

	pocketful_demand = get_total_demand(pocketful_bom_no)
	assert pocketful_demand == 30  # test data of 10 + SO of 5 + MR of 15

	tower_demand = get_total_demand(tower_bom_no)
	assert tower_demand == 35  # test data of 20 + SO of 10 + MR of 5
