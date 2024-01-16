import frappe
import pytest
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
from frappe.exceptions import ValidationError


def test_overproduction():
	# BOM with overproduction_percentage_for_work_order configures
	work_order = frappe.get_doc("Work Order", {"item_name": "Ambrosia Pie"})
	se = make_stock_entry(
		work_order_id=work_order.name, purpose="Material Transfer for Manufacture", qty=work_order.qty
	)
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.update(se)

	assert stock_entry.check_if_operations_completed() is None

	overproduction_percentage_for_work_order = frappe.db.get_value(
		"BOM", stock_entry.bom_no, "overproduction_percentage_for_work_order"
	)
	qty = work_order.qty * (1 + overproduction_percentage_for_work_order / 100)
	se = make_stock_entry(
		work_order_id=work_order.name, purpose="Material Transfer for Manufacture", qty=qty
	)
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.update(se)
	assert stock_entry.check_if_operations_completed() is None

	with pytest.raises(ValidationError) as exc_info:
		qty = qty + 1
		se = make_stock_entry(
			work_order_id=work_order.name, purpose="Material Transfer for Manufacture", qty=qty
		)
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.update(se)
		stock_entry.check_if_operations_completed()

	assert (
		f"is greater than the Work Order's quantity to manufacture of {work_order.qty} plus the overproduction allowance of {overproduction_percentage_for_work_order}%"
		in exc_info.value.args[0]
	)

	# BOM without overproduction_percentage_for_work_order configured
	work_order = frappe.get_doc("Work Order", {"item_name": "Double Plum Pie"})
	overproduction_percentage_for_work_order = frappe.db.get_value(
		"BOM", work_order.bom_no, "overproduction_percentage_for_work_order"
	)
	assert overproduction_percentage_for_work_order == 0.0

	overproduction_percentage_for_work_order = frappe.get_value(
		"Inventory Tools Settings", work_order.company, "overproduction_percentage_for_work_order"
	)
	assert overproduction_percentage_for_work_order != 0.0

	qty = work_order.qty * (1 + overproduction_percentage_for_work_order / 100)
	se = make_stock_entry(
		work_order_id=work_order.name, purpose="Material Transfer for Manufacture", qty=qty
	)
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.update(se)
	assert stock_entry.check_if_operations_completed() is None

	with pytest.raises(ValidationError) as exc_info:
		qty = qty + 1
		se = make_stock_entry(
			work_order_id=work_order.name, purpose="Material Transfer for Manufacture", qty=qty
		)
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.update(se)
		stock_entry.check_if_operations_completed()

	assert (
		f"is greater than the Work Order's quantity to manufacture of {work_order.qty} plus the overproduction allowance of {overproduction_percentage_for_work_order}%"
		in exc_info.value.args[0]
	)
