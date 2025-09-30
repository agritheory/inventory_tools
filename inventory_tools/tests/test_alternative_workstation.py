# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import nowdate


@pytest.fixture(scope="module")
def workstations():
	"""Create two workstations: primary and alternative"""
	ws1_name = "WS-Primary-Alt-Test"
	ws2_name = "WS-Alternative-Alt-Test"

	# Check if workstations already exist
	if not frappe.db.exists("Workstation", ws1_name):
		ws1 = frappe.get_doc(
			{
				"doctype": "Workstation",
				"workstation_name": ws1_name,
				"hour_rate": 100,
			}
		).insert(ignore_permissions=True)
	else:
		ws1 = frappe.get_doc("Workstation", ws1_name)

	if not frappe.db.exists("Workstation", ws2_name):
		ws2 = frappe.get_doc(
			{
				"doctype": "Workstation",
				"workstation_name": ws2_name,
				"hour_rate": 90,
			}
		).insert(ignore_permissions=True)
	else:
		ws2 = frappe.get_doc("Workstation", ws2_name)

	yield ws1, ws2

	# Cleanup
	if frappe.db.exists("Workstation", ws1.name):
		frappe.delete_doc("Workstation", ws1.name, force=1, ignore_permissions=True)
	if frappe.db.exists("Workstation", ws2.name):
		frappe.delete_doc("Workstation", ws2.name, force=1, ignore_permissions=True)


@pytest.fixture
def operation(workstations):
	"""Create an operation with primary and alternative workstation"""
	op_name = "Alt-WS-Test-Operation"

	if not frappe.db.exists("Operation", op_name):
		op = frappe.get_doc(
			{
				"doctype": "Operation",
				"name": op_name,
				"operation": op_name,
				"workstation": workstations[0].name,
				"alternative_workstations": [{"workstation": workstations[1].name}],
			}
		).insert(ignore_permissions=True)
	else:
		op = frappe.get_doc("Operation", op_name)
		op.workstation = workstations[0].name
		op.alternative_workstations = []
		op.append("alternative_workstations", {"workstation": workstations[1].name})
		op.save(ignore_permissions=True)

	yield op

	if frappe.db.exists("Operation", op.name):
		frappe.delete_doc("Operation", op.name, force=1, ignore_permissions=True)


@pytest.fixture
def bom(workstations, operation):
	"""Create a BOM that uses the primary workstation and one raw material"""
	finished_item_code = "ALT-WS-TEST-ITEM"
	raw_item_code = "ALT-WS-RAW-MAT"

	# Finished good item
	if not frappe.db.exists("Item", finished_item_code):
		fg_item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": finished_item_code,
				"item_name": "Alt WS Test Item",
				"is_stock_item": 1,
				"stock_uom": "Nos",
				"item_group": "All Item Groups",
			}
		).insert(ignore_permissions=True)
	else:
		fg_item = frappe.get_doc("Item", finished_item_code)

		# Raw material item
	if not frappe.db.exists("Item", raw_item_code):
		rm_item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": raw_item_code,
				"item_name": "Alt WS Raw Material",
				"is_stock_item": 1,
				"stock_uom": "Nos",
				"item_group": "All Item Groups",
			}
		).insert(ignore_permissions=True)
	else:
		rm_item = frappe.get_doc("Item", raw_item_code)

		# Create BOM with operations + raw materials
	bom_doc = frappe.get_doc(
		{
			"doctype": "BOM",
			"item": fg_item.name,
			"quantity": 1,
			"is_active": 1,
			"with_operations": 1,
			"operations": [
				{
					"operation": operation.name,
					"workstation": workstations[0].name,
					"time_in_mins": 10,
					"qty": 1,
				}
			],
			"items": [
				{
					"item_code": rm_item.item_code,
					"qty": 1,
					"uom": "Nos",
				}
			],
		}
	).insert(ignore_permissions=True)

	if bom_doc.docstatus == 0:
		bom_doc.submit()
	return bom_doc, fg_item


@pytest.mark.order(46)
def test_work_order_with_alternative_ws(bom, workstations, operation):
	"""
	Test that Workstation validation with alternative workstation
	selected allows save/submit of Work Order
	"""
	bom_doc, item = bom
	company = frappe.defaults.get_defaults().get("company")
	warehouse = frappe.db.get_value("Warehouse", {"is_group": 0, "company": company}, "name")

	if not warehouse:
		warehouse = frappe.db.get_value("Warehouse", {"is_group": 0}, "name")

	wo = frappe.get_doc(
		{
			"doctype": "Work Order",
			"production_item": item.name,
			"bom_no": bom_doc.name,
			"qty": 1,
			"company": company,
			"wip_warehouse": warehouse,
			"fg_warehouse": warehouse,
			"operations": [
				{
					"operation": operation.name,
					"workstation": workstations[1].name,
					"time_in_mins": 10,
					"qty": 1,
				}
			],
		}
	)

	try:
		wo.insert(ignore_permissions=True)

		assert wo.name
		assert wo.operations[0].workstation == workstations[1].name

		wo.submit()
		assert wo.docstatus == 1

	finally:
		# Cleanup
		if wo.name and frappe.db.exists("Work Order", wo.name):
			if wo.docstatus == 1:
				wo.cancel()
			frappe.delete_doc("Work Order", wo.name, force=1, ignore_permissions=True)


@pytest.mark.order(47)
def test_job_card_with_alternative_ws(bom, workstations, operation):
	"""
	Test that Workstation validation with alternative workstation
	selected allows save/submit of Job Card
	"""
	bom_doc, item = bom
	company = frappe.defaults.get_defaults().get("company")
	warehouse = frappe.db.get_value("Warehouse", {"is_group": 0, "company": company}, "name")

	if not warehouse:
		warehouse = frappe.db.get_value("Warehouse", {"is_group": 0}, "name")

	wo = frappe.get_doc(
		{
			"doctype": "Work Order",
			"production_item": item.name,
			"bom_no": bom_doc.name,
			"qty": 1,
			"company": company,
			"wip_warehouse": warehouse,
			"fg_warehouse": warehouse,
			"operations": [
				{
					"operation": operation.name,
					"workstation": workstations[0].name,
					"time_in_mins": 10,
					"qty": 1,
				}
			],
		}
	)
	wo.insert(ignore_permissions=True)

	jc = None

	try:
		wo.operations[0].workstation = workstations[1].name
		wo.save(ignore_permissions=True)
		wo.reload()
		wo.submit()

		# Get the actual operation row from the work order
		operation_row = wo.operations[0]

		jc = frappe.get_doc(
			{
				"doctype": "Job Card",
				"work_order": wo.name,
				"operation": operation.name,
				"operation_id": operation_row.name,
				"workstation": workstations[1].name,
				"for_quantity": 0,
				"wip_warehouse": wo.wip_warehouse,
				"time_logs": [
					{"from_time": nowdate() + " 09:00:00", "to_time": nowdate() + " 09:05:00", "completed_qty": 1}
				],
				"flags": {"ignore_validate_qty": True},
			}
		)
		jc.insert(ignore_permissions=True)

		assert jc.name
		assert jc.workstation == workstations[1].name

		jc.submit()
		assert jc.docstatus == 1

	finally:
		# Cleanup
		if jc and jc.name and frappe.db.exists("Job Card", jc.name):
			if jc.docstatus == 1:
				jc.cancel()
			frappe.delete_doc("Job Card", jc.name, force=1, ignore_permissions=True)
		if wo.name and frappe.db.exists("Work Order", wo.name):
			wo.reload()
			if wo.docstatus == 1:
				wo.cancel()
			frappe.delete_doc("Work Order", wo.name, force=1, ignore_permissions=True)


@pytest.mark.order(48)
def test_stock_entry_with_alternative_ws(bom, workstations, operation):
	"""
	Test that Workstation validation with alternative workstation
	selected allows save/submit of Stock Entries
	"""
	bom_doc, item = bom
	company = frappe.defaults.get_defaults().get("company")
	warehouse = frappe.db.get_value("Warehouse", {"is_group": 0, "company": company}, "name")

	if not warehouse:
		warehouse = frappe.db.get_value("Warehouse", {"is_group": 0}, "name")

	wo = frappe.get_doc(
		{
			"doctype": "Work Order",
			"production_item": item.name,
			"bom_no": bom_doc.name,
			"qty": 1,
			"company": company,
			"wip_warehouse": warehouse,
			"fg_warehouse": warehouse,
			"operations": [
				{
					"operation": operation.name,
					"workstation": workstations[1].name,
					"time_in_mins": 10,
					"qty": 1,
				}
			],
		}
	)

	se = None

	try:
		wo.insert(ignore_permissions=True)
		wo.submit()

		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Manufacture",
				"work_order": wo.name,
				"company": company,
				"from_bom": 1,
				"bom_no": bom_doc.name,
				"items": [
					{
						"item_code": item.name,
						"t_warehouse": wo.fg_warehouse,
						"s_warehouse": "",
						"qty": 1,
						"uom": "Nos",
						"allow_zero_valuation_rate": 1,
					}
				],
				"fg_completed_qty": 1,
			}
		)
		se.insert(ignore_permissions=True)

		assert se.name
		assert se.work_order == wo.name

		se.submit()
		assert se.docstatus == 1

	finally:
		# Cleanup
		if se and se.name and frappe.db.exists("Stock Entry", se.name):
			se.reload()
			if se.docstatus == 1:
				se.cancel()
			frappe.delete_doc("Stock Entry", se.name, force=1, ignore_permissions=True)
		if wo.name and frappe.db.exists("Work Order", wo.name):
			wo.reload()
			if wo.docstatus == 1:
				wo.cancel()
			frappe.delete_doc("Work Order", wo.name, force=1, ignore_permissions=True)
