# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import getdate
from inventory_tools.tests.fixtures import workstations
from inventory_tools.inventory_tools.doctype.workstation_operating_cost.workstation_operating_cost import (
	get_operating_cost_per_unit_with_date_range,
)


@pytest.fixture(scope="module")
def setup_data():
	"""Ensure Mixer Station exists with operating cost data from fixtures."""
	ws_data = next(ws for ws in workstations if ws["name"] == "Mixer Station")
	ws_name = ws_data["name"]

	if not frappe.db.exists("Workstation", ws_name):
		ws = frappe.get_doc(
			{
				"doctype": "Workstation",
				"workstation_name": ws_name,
				"hour_rate": ws_data["hour_rate"],
				"workstation_operating_cost": ws_data["operating_costs"],  # 👈 use fixture data
			}
		).insert(ignore_permissions=True)
	else:
		ws = frappe.get_doc("Workstation", ws_name)
		ws.set("workstation_operating_cost", ws_data["operating_costs"])
		ws.save(ignore_permissions=True)

	# Create a simple item + BOM using this workstation
	item_code = "TEST-FIXTURE-ITEM"
	if not frappe.db.exists("Item", item_code):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 1,
				"include_item_in_manufacturing": 1,
				"item_group": "Baked Goods",
				"stock_uom": "Nos",
			}
		).insert(ignore_permissions=True)

	bom = frappe.get_doc(
		{
			"doctype": "BOM",
			"item": item_code,
			"quantity": 1,
			"operations": [{"operation": "Mix Dough Op", "workstation": ws_name, "time_in_mins": 30}],
		}
	).insert(ignore_permissions=True)
	bom.submit()

	wo = frappe.get_doc(
		{
			"doctype": "Work Order",
			"production_item": item_code,
			"bom_no": bom.name,
			"qty": 10,
			"fg_warehouse": "Stores - T",
		}
	).insert(ignore_permissions=True)

	return wo


def test_operating_cost_changes_with_date(setup_data):
	"""Ensure operating cost changes for different date ranges."""
	wo = setup_data
	old_date = getdate("2024-06-15")
	new_date = getdate("2025-06-15")

	old_cost = get_operating_cost_per_unit_with_date_range(work_order=wo, posting_date=old_date)
	new_cost = get_operating_cost_per_unit_with_date_range(work_order=wo, posting_date=new_date)

	print(f"Old cost ({old_date}): {old_cost}")
	print(f"New cost ({new_date}): {new_cost}")

	assert old_cost != new_cost, "Operating cost should differ for different date ranges"
