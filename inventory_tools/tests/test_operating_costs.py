# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

# test_workstation_operating_costs.py
import pytest
import frappe
from frappe.utils import flt
from inventory_tools.inventory_tools.doctype.workstation_operating_cost.workstation_operating_cost import (
	get_operating_cost_per_unit_with_date_range,
)


@pytest.fixture(scope="module")
def setup_test_data():
	"""Setup test data once for all tests"""
	from inventory_tools.tests.setup import before_test

	# Ensure test data exists
	if not frappe.db.exists("Company", "Ambrosia Pie Company"):
		before_test()

	frappe.db.commit()

	yield

	# Cleanup after all tests
	frappe.db.rollback()


@pytest.fixture
def workstation_data():
	"""Fixture providing workstation test data"""
	workstation_name = "Mixer Station"

	if not frappe.db.exists("Workstation", workstation_name):
		pytest.skip(f"Workstation {workstation_name} not found in fixtures")

	workstation = frappe.get_doc("Workstation", workstation_name)

	if not workstation.workstation_operating_cost:
		pytest.skip("No operating costs configured for test workstation")

	return {
		"name": workstation_name,
		"doc": workstation,
		"operating_costs": {
			"2024": {"electricity": 2.82, "consumable": 5.64, "rent": 1.88},
			"2025": {"electricity": 3.00, "consumable": 6.00, "rent": 2.00},
			"2026": {"electricity": 3.18, "consumable": 6.36, "rent": 2.12},
		},
	}


@pytest.fixture
def bom_data():
	"""Fixture providing BOM test data"""
	item = "Bayberry Popper"  # Uses Mixer Station
	bom_no = frappe.get_value("BOM", {"item": item, "is_default": 1})

	if not bom_no:
		pytest.skip(f"No default BOM found for {item}")

	return {"item": item, "bom_no": bom_no, "qty": 5}


@pytest.fixture
def work_order_factory(setup_test_data, bom_data):
	"""Factory fixture to create work orders with different dates"""
	created_work_orders = []

	def _create_work_order(posting_date):
		wo = frappe.new_doc("Work Order")
		wo.production_item = bom_data["item"]
		wo.bom_no = bom_data["bom_no"]
		wo.qty = bom_data["qty"]
		wo.company = "Ambrosia Pie Company"
		wo.wip_warehouse = "Kitchen - APC"
		wo.fg_warehouse = "Refrigerated Display - APC"
		wo.planned_start_date = posting_date
		wo.save()
		wo.submit()

		# Complete operations
		for operation in wo.operations:
			job_cards = frappe.get_all(
				"Job Card", {"work_order": wo.name, "operation": operation.operation}
			)

			for jc_name in job_cards:
				jc = frappe.get_doc("Job Card", jc_name.name)
				jc.append(
					"time_logs",
					{
						"from_time": f"{posting_date} 09:00:00",
						"to_time": f"{posting_date} 10:00:00",
						"completed_qty": wo.qty,
						"time_in_mins": operation.time_in_mins or 60,
					},
				)
				jc.save()
				jc.submit()

		wo.reload()
		created_work_orders.append(wo.name)
		return wo

	yield _create_work_order

	# Cleanup created work orders
	for wo_name in created_work_orders:
		try:
			if frappe.db.exists("Work Order", wo_name):
				wo = frappe.get_doc("Work Order", wo_name)
				if wo.docstatus == 1:
					wo.cancel()
		except Exception as e:
			print(f"Error cleaning up work order {wo_name}: {e}")


def test_operating_cost_with_backdated_rate(
	setup_test_data, workstation_data, bom_data, work_order_factory
):
	"""Test that backdated operating costs (2024) are applied correctly"""
	posting_date = "2024-06-15"
	wo = work_order_factory(posting_date)

	# Calculate operating cost using the imported function
	operating_cost_per_unit = get_operating_cost_per_unit_with_date_range(
		work_order=wo, posting_date=posting_date
	)

	# Expected cost for 2024 (backdated rates)
	costs_2024 = workstation_data["operating_costs"]["2024"]
	expected_cost_per_unit = (
		costs_2024["electricity"] + costs_2024["consumable"] + costs_2024["rent"]
	) / bom_data["qty"]

	assert flt(operating_cost_per_unit, 2) == flt(
		expected_cost_per_unit, 2
	), f"Expected operating cost per unit {expected_cost_per_unit}, got {operating_cost_per_unit}"


def test_operating_cost_with_current_rate(
	setup_test_data, workstation_data, bom_data, work_order_factory
):
	"""Test that current operating costs (2025) are applied correctly"""
	posting_date = "2025-06-15"
	wo = work_order_factory(posting_date)

	# Calculate operating cost using the imported function
	operating_cost_per_unit = get_operating_cost_per_unit_with_date_range(
		work_order=wo, posting_date=posting_date
	)

	# Expected cost for 2025 (current rates)
	costs_2025 = workstation_data["operating_costs"]["2025"]
	expected_cost_per_unit = (
		costs_2025["electricity"] + costs_2025["consumable"] + costs_2025["rent"]
	) / bom_data["qty"]

	assert flt(operating_cost_per_unit, 2) == flt(
		expected_cost_per_unit, 2
	), f"Expected operating cost per unit {expected_cost_per_unit}, got {operating_cost_per_unit}"


def test_operating_cost_with_future_rate(
	setup_test_data, workstation_data, bom_data, work_order_factory
):
	"""Test that future operating costs (2026) are applied correctly"""
	posting_date = "2026-06-15"
	wo = work_order_factory(posting_date)

	# Calculate operating cost using the imported function
	operating_cost_per_unit = get_operating_cost_per_unit_with_date_range(
		work_order=wo, posting_date=posting_date
	)

	# Expected cost for 2026 (future rates)
	costs_2026 = workstation_data["operating_costs"]["2026"]
	expected_cost_per_unit = (
		costs_2026["electricity"] + costs_2026["consumable"] + costs_2026["rent"]
	) / bom_data["qty"]

	assert flt(operating_cost_per_unit, 2) == flt(
		expected_cost_per_unit, 2
	), f"Expected operating cost per unit {expected_cost_per_unit}, got {operating_cost_per_unit}"
