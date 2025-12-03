# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry


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


def test_operating_cost_changes():
	"""
	Test that operating costs are properly capitalized into finished goods during manufacture.
	Transfer for Manufacture:
	| Account                                    | Stock Ledger | Debit    | Credit   |
	|--------------------------------------------|--------------|----------|----------|
	| 1410 - Stock In Hand - APC                 |  Various     |          |   150.98 |
	| 1110 - Work In Process - APC               |  Various     |   150.98 |          |

	Manufacture:
	| Account                                    | Stock Ledger | Debit    | Credit   |
	|--------------------------------------------|--------------|----------|----------|
	| 1410 - Stock In Hand - APC                 | Various      | 240.98   |          |
	| 2212 - Accrued Manufacturing Wages - APC   |              |          | 10.00    |
	| 2213 - Accrued Manufacturing Electricity   |              |          | 41.50    |
	| 2214 - Accrued Manufacturing Rent - APC    |              |          | 32.00    |
	| 1110 - Work In Process - APC               |              |          | 150.98   |

	Verifies that 50 units of Pie Crust complete manufacturing with:
	- Raw materials consumed: $150.98
	- Operating costs capitalized: $83.50
	- Total finished goods valuation: $234.48 ($4.69 per unit)
	"""

	wo = frappe.get_doc("Work Order", "MFG-WO-2025-00016")
	submit_all_purchase_receipts()

	se = make_stock_entry(wo.name, "Material Transfer for Manufacture", 50)
	se = frappe.get_doc(**se)
	se.save()
	material_receipt = frappe.copy_doc(se)
	material_receipt.stock_entry_type = "Material Receipt"
	for row in material_receipt.items:
		row.t_warehouse = row.s_warehouse
		row.s_warehouse = None
		row.expense_account = "5119 - Stock Adjustment - APC"
	material_receipt.save()
	material_receipt.submit()
	se.submit()

	complete_job_cards_for_work_order(wo.name)

	sem = make_stock_entry(wo.name, "Manufacture", 50)
	sem = frappe.get_doc(**sem)
	sem.save()
	sem.submit()

	assert sem.fg_completed_qty == 50
	assert flt(sem.total_incoming_value, 2) == 234.48
	assert flt(sem.total_outgoing_value, 2) == 150.98
	assert flt(sem.total_additional_costs, 2) == 83.5
	fg_item = [item for item in sem.items if item.is_finished_item][0]
	assert fg_item.qty == 50
	assert flt(fg_item.basic_rate, 4) == 3.0196  # $150.98 / 50 units
	assert flt(fg_item.additional_cost, 2) == 83.5  # Operating costs per finished item line
	assert flt(fg_item.valuation_rate, 4) == 4.6896  # ($150.98 + $83.50) / 50 units
	wages_cost = sum(cost.amount for cost in sem.additional_costs if "2212" in cost.expense_account)
	electricity_cost = sum(
		cost.amount for cost in sem.additional_costs if "2213" in cost.expense_account
	)
	rent_cost = sum(cost.amount for cost in sem.additional_costs if "2214" in cost.expense_account)
	assert flt(wages_cost, 2) == 10.00
	assert flt(electricity_cost, 2) == 41.50
	assert flt(rent_cost, 2) == 32.00

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
