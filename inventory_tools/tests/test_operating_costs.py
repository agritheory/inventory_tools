# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import pytest
import frappe
from frappe.utils import getdate
from inventory_tools.inventory_tools.doctype.workstation_operating_cost.workstation_operating_cost import (
	get_operating_cost_per_unit_with_date_range,
)


@pytest.fixture(scope="module")
def setup_workstation():
	"""Ensure a test workstation with date-range-based costs exists."""
	ws_name = "Mixer Station"

	# Create Operation first (required for BOM)
	if not frappe.db.exists("Operation", "Mixing"):
		op = frappe.get_doc(
			{
				"doctype": "Operation",
				"name": "Mixing",
				"operation": "Mixing",
				"workstation": ws_name,
			}
		)
		op.insert(ignore_permissions=True)
		frappe.db.commit()

	if not frappe.db.exists("Workstation", ws_name):
		ws = frappe.get_doc(
			{
				"doctype": "Workstation",
				"workstation_name": ws_name,
				"workstation_operating_cost": [
					{
						"from_date": "2024-01-01",
						"to_date": "2024-12-31",
						"electricity_cost": 2.0,
						"consumable_cost": 3.0,
						"rent_cost": 4.0,
					},
					{
						"from_date": "2025-01-01",
						"to_date": "2025-12-31",
						"electricity_cost": 3.0,
						"consumable_cost": 4.0,
						"rent_cost": 5.0,
					},
				],
			}
		)
		ws.insert(ignore_permissions=True)
		frappe.db.commit()

	return frappe.get_doc("Workstation", ws_name)


@pytest.fixture(scope="module")
def setup_bom_and_work_order(setup_workstation):
	"""Create a BOM and Work Order for testing."""
	finished_item = "TEST-MFG-ITEM"
	raw_item = "TEST-RM-ITEM"

	company = frappe.defaults.get_global_default("company") or "Ambrosia Pie Company"
	company_abbr = frappe.db.get_value("Company", company, "abbr") or "APC"
	warehouse_name = f"Stores - {company_abbr}"

	# Ensure the warehouse exists
	if not frappe.db.exists("Warehouse", warehouse_name):
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "Stores",
				"is_group": 0,
				"company": company,
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()

	# Ensure Items exist
	for item_code, include_mfg in [(finished_item, 1), (raw_item, 0)]:
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": item_code,
					"is_stock_item": 1,
					"include_item_in_manufacturing": include_mfg,
					"item_group": "All Item Groups",
					"stock_uom": "Nos",
				}
			).insert(ignore_permissions=True)

	# Delete existing BOM if it exists (for clean test)
	existing_bom = frappe.db.get_value("BOM", {"item": finished_item})
	if existing_bom:
		bom = frappe.get_doc("BOM", existing_bom)
		if bom.docstatus == 1:
			bom.cancel()
		frappe.delete_doc("BOM", existing_bom)
		frappe.db.commit()

	# Create and submit BOM with operations enabled
	bom = frappe.get_doc(
		{
			"doctype": "BOM",
			"item": finished_item,
			"quantity": 1,
			"company": company,
			"with_operations": 1,
			"items": [{"item_code": raw_item, "qty": 1, "uom": "Nos"}],
			"operations": [
				{
					"operation": "Mixing",
					"workstation": setup_workstation.name,
					"time_in_mins": 30,
					"hour_rate": 10,
				}
			],
		}
	).insert(ignore_permissions=True)

	bom.submit()
	frappe.db.commit()

	# Create Work Order with operations manually
	wo = frappe.get_doc(
		{
			"doctype": "Work Order",
			"production_item": finished_item,
			"bom_no": bom.name,
			"qty": 10,
			"company": company,
			"fg_warehouse": warehouse_name,
			"wip_warehouse": warehouse_name,
		}
	)

	# Manually copy operations from BOM
	for bom_op in bom.operations:
		wo.append(
			"operations",
			{
				"operation": bom_op.operation,
				"workstation": bom_op.workstation,
				"time_in_mins": bom_op.time_in_mins,
				"hour_rate": bom_op.hour_rate or 10,
			},
		)

	wo.insert(ignore_permissions=True)
	frappe.db.commit()
	wo.reload()

	return wo


def test_operating_cost_changes_with_posting_date(setup_bom_and_work_order):
	"""Ensure Manufacture Stock Entry cost changes with posting date ranges."""
	wo = setup_bom_and_work_order

	# Get the workstation to calculate expected costs
	ws = frappe.get_doc("Workstation", "Mixer Station")

	# Find operating costs for each date
	old_date = getdate("2024-06-15")
	new_date = getdate("2025-06-15")

	cost_2024 = None
	cost_2025 = None

	for oc in ws.workstation_operating_cost:
		if getdate(oc.from_date) <= old_date <= getdate(oc.to_date):
			cost_2024 = oc.electricity_cost + oc.consumable_cost + oc.rent_cost
		if getdate(oc.from_date) <= new_date <= getdate(oc.to_date):
			cost_2025 = oc.electricity_cost + oc.consumable_cost + oc.rent_cost

	# Calculate expected costs
	time_in_mins = wo.operations[0].time_in_mins
	hours = time_in_mins / 60.0

	expected_2024 = (hours * cost_2024) / wo.qty
	expected_2025 = (hours * cost_2025) / wo.qty

	# Get actual costs
	actual_2024 = get_operating_cost_per_unit_with_date_range(work_order=wo, posting_date=old_date)
	actual_2025 = get_operating_cost_per_unit_with_date_range(work_order=wo, posting_date=new_date)

	# Main assertions
	assert (
		actual_2025 != actual_2024
	), "Operating cost should change with different posting date ranges"
	assert actual_2024 > 0, "2024 cost should be greater than 0"
	assert actual_2025 > 0, "2025 cost should be greater than 0"
	assert actual_2025 > actual_2024, "2025 cost should be higher than 2024 cost"

	# Verify calculations are close to expected
	tolerance = 0.01
	assert (
		abs(actual_2024 - expected_2024) < tolerance
	), f"Expected {expected_2024} for 2024, got {actual_2024}"
	assert (
		abs(actual_2025 - expected_2025) < tolerance
	), f"Expected {expected_2025} for 2025, got {actual_2025}"
