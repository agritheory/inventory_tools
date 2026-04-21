# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import flt
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry


@pytest.mark.order(49)
def test_stock_entry_material_transfer_routes_to_quarantine():
	"""Material Transfer for Manufacture redirects inspection-required items to quarantine (before_submit hook)."""
	settings = frappe.get_doc("Inventory Tools Settings", "Ambrosia Pie Company")
	settings.enable_quarantine_workflow = 1
	settings.save()

	cornstarch = frappe.get_doc("Item", "Cornstarch")
	cornstarch.quality_inspection_template = "Ingredient QC"
	cornstarch.save()
	apc_default = next(
		(d for d in cornstarch.item_defaults if d.company == "Ambrosia Pie Company"),
		None,
	)
	if apc_default:
		apc_default.inspection_required_before_manufacture = 1
	else:
		cornstarch.append(
			"item_defaults",
			{"company": "Ambrosia Pie Company", "inspection_required_before_manufacture": 1},
		)
	cornstarch.save()

	wo_list = frappe.get_all(
		"Work Order",
		filters={"company": "Ambrosia Pie Company", "docstatus": 1},
		fields=["name", "production_item"],
	)
	wo_with_cornstarch = None
	for wo in wo_list:
		if frappe.get_all("Work Order Item", {"parent": wo.name, "item_code": "Cornstarch"}, limit=1):
			wo_with_cornstarch = wo.name
			break
	assert wo_with_cornstarch, "No Work Order with Cornstarch in test data"

	se_dict = make_stock_entry(wo_with_cornstarch, "Material Transfer for Manufacture", 50)
	se = frappe.get_doc(**se_dict)
	se.save()
	# Add stock to source warehouses (same pattern as test_operating_cost_changes)
	material_receipt = frappe.copy_doc(se)
	material_receipt.stock_entry_type = "Material Receipt"
	for row in material_receipt.items:
		row.t_warehouse = row.s_warehouse
		row.s_warehouse = None
		row.expense_account = "5119 - Stock Adjustment - APC"
	material_receipt.save()
	material_receipt.submit()
	se.submit()  # before_submit hook runs quarantine redirect

	se.reload()
	cornstarch_row = next((r for r in se.items if r.item_code == "Cornstarch"), None)
	assert cornstarch_row is not None
	assert cornstarch_row.t_warehouse == "Quarantine - APC"
	assert cornstarch_row.intended_warehouse == "Kitchen - APC"

	cornstarch.reload()
	cornstarch.quality_inspection_template = None
	apc_default = next(
		(d for d in cornstarch.item_defaults if d.company == "Ambrosia Pie Company"),
		None,
	)
	if apc_default:
		apc_default.inspection_required_before_manufacture = 0
	cornstarch.save()


def submit_all_purchase_receipts():
	for pr in frappe.get_all("Purchase Receipt", {"docstatus": 0}):
		pr = frappe.get_doc("Purchase Receipt", pr)
		pr.submit()


def complete_job_cards_for_work_order(wo):
	job_cards = frappe.get_all("Job Card", {"work_order": wo}, order_by="sequence_id ASC")
	for jc in job_cards:
		doc = frappe.get_doc("Job Card", jc.name)
		for row in doc.scheduled_time_logs:
			doc.append(
				"time_logs",
				{"from_time": row.from_time, "to_time": row.to_time, "completed_qty": doc.for_quantity},
			)
		doc.save()
		doc.submit()


@pytest.mark.order(50)
def test_operating_cost_changes():
	"""
	Test that operating costs are properly capitalized into finished goods during manufacture.

	This test verifies:
	1. Raw materials are consumed at their proper valuation rates
	2. Operating costs (wages, electricity, rent) from job cards are capitalized
	3. Finished goods valuation = raw materials + operating costs
	4. GL entries are created for the operating cost accrual accounts

	TODO: After test database reinstall, verify telemetry output shows expected values:
	- All raw materials should have non-zero valuation_rate from Bakery Buying price list
	- total_outgoing should reflect actual BOM item costs
	- Review and potentially add specific value assertions once data is stable
	"""

	# Find the In House Pie Crust Work Order (supplier field empty = not subcontracted)
	# Filter for non-subcontracted (In House) Work Order - supplier field should be empty
	wo_name = frappe.db.get_value(
		"Work Order",
		{
			"production_item": "Pie Crust",
			"company": "Ambrosia Pie Company",
			"docstatus": 1,
			"supplier": ("is", "not set"),
		},
		"name",
		order_by="creation asc",
	)
	assert (
		wo_name
	), "No submitted In House Work Order for Pie Crust (Ambrosia Pie Company) in test data"
	wo = frappe.get_doc("Work Order", wo_name)
	submit_all_purchase_receipts()

	se = make_stock_entry(wo.name, "Material Transfer for Manufacture", 50)
	se = frappe.get_doc(**se)
	se.save()
	# Create Material Receipt with proper valuations from Bakery Buying price list
	material_receipt = frappe.copy_doc(se)
	material_receipt.stock_entry_type = "Material Receipt"
	for row in material_receipt.items:
		row.t_warehouse = row.s_warehouse
		row.s_warehouse = None
		row.expense_account = "5119 - Stock Adjustment - APC"
		# Set basic_rate from price list to ensure proper valuation
		price_list_rate = frappe.db.get_value(
			"Item Price",
			{"item_code": row.item_code, "price_list": "Bakery Buying", "buying": 1},
			"price_list_rate",
		)
		if price_list_rate:
			row.basic_rate = price_list_rate
	material_receipt.save()
	material_receipt.submit()
	se.submit()

	complete_job_cards_for_work_order(wo.name)

	sem = make_stock_entry(wo.name, "Manufacture", 50)
	sem = frappe.get_doc(**sem)
	sem.save()
	sem.submit()
	assert sem.fg_completed_qty == 50

	# Core assertion: total incoming = raw materials + operating costs
	assert flt(sem.total_incoming_value, 2) == flt(
		sem.total_outgoing_value + sem.total_additional_costs, 2
	)

	# Verify operating costs are non-zero and capitalized
	assert sem.total_additional_costs > 0, "Operating costs should be capitalized"
	assert sem.total_outgoing_value > 0, "Raw materials should have value"

	fg_item = [item for item in sem.items if item.is_finished_item][0]
	assert fg_item.qty == 50
	# FG basic_rate = raw materials / qty
	assert flt(fg_item.basic_rate, 2) == flt(sem.total_outgoing_value / 50, 2)
	# FG additional_cost = total operating costs
	assert flt(fg_item.additional_cost, 2) == flt(sem.total_additional_costs, 2)
	# FG valuation_rate = (raw materials + operating costs) / qty
	assert flt(fg_item.valuation_rate, 2) == flt(
		(sem.total_outgoing_value + sem.total_additional_costs) / 50, 2
	)

	# Verify operating cost breakdown by account
	wages_cost = sum(cost.amount for cost in sem.additional_costs if "2212" in cost.expense_account)
	electricity_cost = sum(
		cost.amount for cost in sem.additional_costs if "2213" in cost.expense_account
	)
	rent_cost = sum(cost.amount for cost in sem.additional_costs if "2214" in cost.expense_account)
	assert wages_cost > 0, "Wages should be accrued"
	assert electricity_cost > 0, "Electricity should be accrued"
	assert rent_cost > 0, "Rent should be accrued"
	assert flt(wages_cost + electricity_cost + rent_cost, 2) == flt(sem.total_additional_costs, 2)

	gl_entries = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": "Stock Entry", "voucher_no": sem.name},
		fields=["account", "debit", "credit"],
	)

	accounts_in_gl = {entry["account"]: entry for entry in gl_entries}
	assert "2212 - Accrued Manufacturing Wages - APC" in accounts_in_gl
	assert "2213 - Accrued Manufacturing Electricity - APC" in accounts_in_gl
	assert "2214 - Accrued Manufacturing Rent Contribution - APC" in accounts_in_gl

	total_debit = sum(entry["debit"] for entry in gl_entries)
	total_credit = sum(entry["credit"] for entry in gl_entries)
	assert flt(total_debit, 2) == flt(total_credit, 2)
