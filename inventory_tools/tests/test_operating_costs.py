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

	return frappe.get_doc("Workstation", ws_name)


def test_operating_cost_changes_with_posting_date():
	"""Ensure Manufacture Stock Entry cost changes with posting date ranges."""
	wo = frappe.get_doc("Work Order", "MFG-WO-2025-00016")

	ws = frappe.get_doc("Workstation", "Mixer Station")

	old_date = getdate("2024-06-15")
	new_date = getdate("2025-06-15")

	cost_2024 = None
	cost_2025 = None

	for oc in ws.workstation_operating_cost:
		if getdate(oc.from_date) <= old_date <= getdate(oc.to_date):
			cost_2024 = oc.electricity_cost + oc.consumable_cost + oc.rent_cost
		if getdate(oc.from_date) <= new_date <= getdate(oc.to_date):
			cost_2025 = oc.electricity_cost + oc.consumable_cost + oc.rent_cost

	time_in_mins = wo.operations[0].time_in_mins
	hours = time_in_mins / 60.0

	expected_2024 = (hours * cost_2024) / wo.qty
	expected_2025 = (hours * cost_2025) / wo.qty

	actual_2024 = get_operating_cost_per_unit_with_date_range(work_order=wo, posting_date=old_date)
	actual_2025 = get_operating_cost_per_unit_with_date_range(work_order=wo, posting_date=new_date)

	assert (
		actual_2025 != actual_2024
	), "Operating cost should change with different posting date ranges"
	assert actual_2024 > 0, "2024 cost should be greater than 0"
	assert actual_2025 > 0, "2025 cost should be greater than 0"
	assert actual_2025 > actual_2024, "2025 cost should be higher than 2024 cost"

	tolerance = 3
	assert (
		abs(actual_2024 - expected_2024) < tolerance
	), f"Expected {expected_2024} for 2024, got {actual_2024}"
	assert (
		abs(actual_2025 - expected_2025) < tolerance
	), f"Expected {expected_2025} for 2025, got {actual_2025}"
