# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import add_days, flt, getdate, nowdate

from inventory_tools.inventory_tools.report.warehouse_location_optimization.warehouse_location_optimization import (
	create_putaway_rules,
	execute,
)
from inventory_tools.tests.setup import DEMO_PUTAWAY_PRIORITY
from inventory_tools.warehouse_location_optimization import (
	get_putaway_rules_for_items,
	putaway_capacity_from_row,
	set_putaway_rule_capacity,
	suggest_putaway_rule_capacity,
	warehouse_slot_capacity,
)

COMPANY = "Chelsea Fruit Co"
PLAN = "All Warehouses - CFC"
NEAR_WH = "Fruit Storage 1 - CFC"


def report_filters(**overrides):
	values = {
		"company": COMPANY,
		"warehouse_plan": PLAN,
		"from_date": add_days(nowdate(), -365),
		"to_date": nowdate(),
	}
	values.update(overrides)
	return frappe._dict(values)


@pytest.mark.order(83)
def test_demo_putaway_rules_seeded_from_setup():
	"""before_test installs naive demo rules (priority 50) from items_stockentry.json."""
	from inventory_tools.tests.setup import stockentry_qty_totals_by_item_warehouse

	count = frappe.db.count(
		"Putaway Rule",
		{"company": COMPANY, "priority": DEMO_PUTAWAY_PRIORITY, "disable": 0},
	)
	assert count > 50

	expected_coconut_warehouses = {
		warehouse
		for (item_code, warehouse) in stockentry_qty_totals_by_item_warehouse(COMPANY)
		if item_code == "Coconut"
	}
	coconut_rules = frappe.get_all(
		"Putaway Rule",
		filters={
			"item_code": "Coconut",
			"company": COMPANY,
			"priority": DEMO_PUTAWAY_PRIORITY,
		},
		pluck="warehouse",
	)
	assert coconut_rules
	assert set(coconut_rules) & expected_coconut_warehouses


@pytest.mark.order(84)
def test_warehouse_slot_capacity_from_dimensions():
	assert warehouse_slot_capacity("Cranberry", NEAR_WH) == 3
	assert warehouse_slot_capacity("Cryptocarya Alba", NEAR_WH) == 2
	assert suggest_putaway_rule_capacity("Cranberry", NEAR_WH) == 3
	assert warehouse_slot_capacity("Pie Tin", NEAR_WH) is None


@pytest.mark.order(85)
def test_create_putaway_rule_uses_report_row_capacity():
	row = {
		"item_code": "Coconut",
		"suggested_warehouse": "Fruit Storage 3 - CFC",
		"capacity": 42,
		"qty_moved": 9999,
	}
	assert putaway_capacity_from_row(row) == 42

	result = create_putaway_rules([{**row, "priority": 5}])
	rule_name = (result["created"] or result["updated"])[0]
	assert flt(frappe.db.get_value("Putaway Rule", rule_name, "capacity")) >= 42
	frappe.delete_doc("Putaway Rule", rule_name, force=1)


@pytest.mark.order(86)
def test_get_putaway_rules_for_items_uses_lowest_priority():
	item_code = "Cranberry"
	low_wh = "Fruit Storage 1 - CFC"
	high_wh = "Fruit Storage 2 - CFC"

	low_rule = frappe.new_doc("Putaway Rule")
	low_rule.item_code = item_code
	low_rule.warehouse = low_wh
	low_rule.company = COMPANY
	low_rule.priority = 2
	set_putaway_rule_capacity(low_rule, 200)
	low_rule.insert()

	high_rule = frappe.new_doc("Putaway Rule")
	high_rule.item_code = item_code
	high_rule.warehouse = high_wh
	high_rule.company = COMPANY
	high_rule.priority = 99
	set_putaway_rule_capacity(high_rule, 200)
	high_rule.insert()

	active = get_putaway_rules_for_items([item_code], COMPANY)
	assert active[item_code].warehouse == low_wh
	assert active[item_code].priority == 2

	frappe.delete_doc("Putaway Rule", low_rule.name)
	frappe.delete_doc("Putaway Rule", high_rule.name)


@pytest.mark.order(87)
def test_create_putaway_rule_without_stock_moves():
	item_code = "Cranberry"
	warehouse = NEAR_WH
	slot_capacity = warehouse_slot_capacity(item_code, warehouse)
	assert slot_capacity == 3
	row = {
		"item_code": item_code,
		"suggested_warehouse": warehouse,
		"priority": 5,
		"qty_moved": 40,
		"capacity": slot_capacity,
	}

	before_entries = frappe.db.count("Stock Entry")
	result = create_putaway_rules([row])
	after_entries = frappe.db.count("Stock Entry")

	assert after_entries == before_entries
	assert result["created"] or result["updated"]

	rule_name = frappe.db.get_value(
		"Putaway Rule",
		{"item_code": item_code, "warehouse": warehouse, "company": COMPANY},
		"name",
	)
	assert rule_name
	rule_capacity = frappe.db.get_value("Putaway Rule", rule_name, "capacity")
	assert rule_capacity == row["capacity"]
	frappe.delete_doc("Putaway Rule", rule_name)


@pytest.mark.order(88)
def test_update_putaway_rule_capacity_and_priority():
	item_code = "Coconut"
	warehouse = "Fruit Storage 50 - CFC"

	rule_name = frappe.db.get_value(
		"Putaway Rule",
		{"item_code": item_code, "warehouse": warehouse, "company": COMPANY},
		"name",
	)
	assert rule_name
	original_priority = frappe.db.get_value("Putaway Rule", rule_name, "priority")
	original_capacity = frappe.db.get_value("Putaway Rule", rule_name, "capacity")

	result = create_putaway_rules(
		[{"item_code": item_code, "suggested_warehouse": warehouse, "priority": 4}],
		capacity=250,
	)

	assert result["updated"] == [rule_name]
	assert not result["created"]
	assert frappe.db.get_value("Putaway Rule", rule_name, "capacity") == 250
	assert frappe.db.get_value("Putaway Rule", rule_name, "priority") == 4

	frappe.db.set_value("Putaway Rule", rule_name, "priority", original_priority)
	frappe.db.set_value("Putaway Rule", rule_name, "capacity", original_capacity)


@pytest.mark.order(89)
def test_set_putaway_rule_capacity_covers_on_hand_stock():
	item_code = "Banana"
	warehouse = "Fruit Storage 55 - CFC"

	doc = frappe.new_doc("Putaway Rule")
	doc.item_code = item_code
	doc.warehouse = warehouse
	doc.company = COMPANY
	doc.priority = 3
	set_putaway_rule_capacity(doc, 50)
	doc.insert()

	assert doc.stock_capacity > 0
	assert doc.capacity > 0

	frappe.delete_doc("Putaway Rule", doc.name)


@pytest.mark.order(90)
def test_optimization_apply_changes_active_putaway_rule():
	"""Report apply should install a lower-priority rule that wins over demo priority-50 rules."""
	_columns, rows = execute(report_filters())
	row = next(
		report_row
		for report_row in rows
		if report_row.get("item_code")
		and report_row.get("putaway_warehouse")
		and report_row.get("suggested_warehouse")
		and report_row["putaway_warehouse"] != report_row["suggested_warehouse"]
	)
	demo_warehouse = row["putaway_warehouse"]

	create_putaway_rules(
		[
			{
				"item_code": row["item_code"],
				"suggested_warehouse": row["suggested_warehouse"],
				"priority": row["priority"],
			}
		],
		capacity=200,
	)

	_columns, rows_after = execute(report_filters())
	row_after = next(
		report_row for report_row in rows_after if report_row["item_code"] == row["item_code"]
	)
	assert row_after["putaway_warehouse"] == row["suggested_warehouse"]
	assert row_after["putaway_warehouse"] != demo_warehouse
	assert row_after["priority"] == row["priority"]

	active = get_putaway_rules_for_items([row["item_code"]], COMPANY)
	assert active[row["item_code"]].warehouse == row["suggested_warehouse"]
	assert active[row["item_code"]].priority == row["priority"]


@pytest.mark.order(91)
def test_multi_company_receipt_apply_putaway_rule_setting():
	"""Multi-company PR creation respects Inventory Tools Settings for putaway on receipt.

	Self-contained: does not use Material Demand rows. Order 35 seeds Southern Fruit
	demand into submitted POs/PRs, and setup already satisfies Bayberry — so by order 91
	those report rows are gone.
	"""
	from erpnext.stock.doctype.material_request.material_request import make_purchase_order
	from inventory_tools.inventory_tools.overrides.purchase_order import (
		build_purchase_receipt_for_company,
	)

	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	original_putaway = settings.apply_putaway_rule_on_multi_company_receipt
	settings.purchase_order_aggregation_company = settings.name
	settings.aggregated_purchasing_warehouse = None
	settings.apply_putaway_rule_on_multi_company_receipt = 1
	settings.save()

	item_code = "Coconut"
	slot_warehouse = "Fruit Storage 55 - CFC"
	mr_warehouse = "Stores - CFC"
	stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")

	rule = frappe.new_doc("Putaway Rule")
	rule.company = "Chelsea Fruit Co"
	rule.item_code = item_code
	rule.warehouse = slot_warehouse
	rule.priority = 1
	set_putaway_rule_capacity(rule, 500)
	rule.insert()

	mr = frappe.new_doc("Material Request")
	mr.company = "Chelsea Fruit Co"
	mr.material_request_type = "Purchase"
	mr.schedule_date = getdate()
	mr.append(
		"items",
		{
			"item_code": item_code,
			"qty": 5,
			"schedule_date": getdate(),
			"warehouse": mr_warehouse,
			"uom": stock_uom,
		},
	)
	mr.insert()
	mr.submit()

	po = make_purchase_order(mr.name)
	po.supplier = "Southern Fruit Supply"
	po.buying_price_list = "Bakery Buying"
	po.multi_company_purchase_order = 1
	po.schedule_date = getdate()
	for item in po.items:
		item.requesting_company = "Chelsea Fruit Co"
		item.warehouse = mr_warehouse
		item.schedule_date = getdate()
	po.save()
	po.submit()
	po_item = po.items[0]
	assert po_item.warehouse == mr_warehouse
	assert po_item.warehouse != slot_warehouse

	pr = build_purchase_receipt_for_company(po.name, "Chelsea Fruit Co", [po_item.name])
	assert pr.apply_putaway_rule == 1
	pr.save()
	assert pr.items[0].warehouse == slot_warehouse
	frappe.delete_doc("Purchase Receipt", pr.name, force=1)
	po.reload()
	po.cancel()
	frappe.delete_doc("Purchase Order", po.name, force=1)

	settings.apply_putaway_rule_on_multi_company_receipt = 0
	settings.save()

	po = make_purchase_order(mr.name)
	po.supplier = "Southern Fruit Supply"
	po.buying_price_list = "Bakery Buying"
	po.multi_company_purchase_order = 1
	po.schedule_date = getdate()
	for item in po.items:
		item.requesting_company = "Chelsea Fruit Co"
		item.warehouse = mr_warehouse
		item.schedule_date = getdate()
	po.save()
	po.submit()
	po_item = po.items[0]

	pr = build_purchase_receipt_for_company(po.name, "Chelsea Fruit Co", [po_item.name])
	assert pr.apply_putaway_rule == 0
	pr.save()
	assert pr.items[0].warehouse == mr_warehouse

	frappe.delete_doc("Purchase Receipt", pr.name, force=1)
	po.reload()
	po.cancel()
	frappe.delete_doc("Purchase Order", po.name, force=1)
	mr.reload()
	mr.cancel()
	frappe.delete_doc("Material Request", mr.name, force=1)
	frappe.delete_doc("Putaway Rule", rule.name, force=1)

	settings.apply_putaway_rule_on_multi_company_receipt = original_putaway
	settings.save()
