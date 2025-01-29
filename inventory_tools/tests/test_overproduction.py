import frappe
import pytest
from erpnext.manufacturing.doctype.work_order.work_order import create_job_card, make_stock_entry
from frappe.exceptions import ValidationError
from frappe.utils import now, strip_html

from inventory_tools.inventory_tools.overrides.work_order import get_allowance_percentage


@pytest.mark.order(30)
def test_get_allowance_percentage():
	work_order = frappe.get_doc("Work Order", {"item_name": "Gooseberry Pie"})
	bom = frappe.get_doc("BOM", work_order.bom_no)

	inventory_tools_settings = frappe.get_doc(
		"Inventory Tools Settings", {"company": work_order.company}
	)
	# No value set
	inventory_tools_settings.overproduction_percentage_for_work_order = 0.00
	inventory_tools_settings.save()
	bom.overproduction_percentage_for_work_order = 0.0
	bom.save()
	assert get_allowance_percentage(work_order.company, bom.name) == 0.0

	# Uses value from inventory tools settings
	inventory_tools_settings.overproduction_percentage_for_work_order = 50.0
	inventory_tools_settings.save()
	bom.overproduction_percentage_for_work_order = 0.0
	bom.save()
	assert get_allowance_percentage(work_order.company, bom.name) == 50.0

	# Uses value from BOM
	inventory_tools_settings.overproduction_percentage_for_work_order = 50.0
	inventory_tools_settings.save()
	bom.overproduction_percentage_for_work_order = 100.0
	bom.save()
	assert get_allowance_percentage(work_order.company, bom.name) == 100.0


@pytest.mark.order(31)
def test_check_if_operations_completed():

	# BOM with overproduction_percentage_for_work_order configured
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


@pytest.mark.order(32)
def test_validate_finished_goods():
	work_order = frappe.get_doc("Work Order", {"item_name": "Ambrosia Pie"})
	se = make_stock_entry(work_order_id=work_order.name, purpose="Manufacture", qty=work_order.qty)
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.update(se)
	assert stock_entry.validate_finished_goods() is None

	with pytest.raises(ValidationError) as exc_info:
		stock_entry.fg_completed_qty = work_order.qty * 10
		stock_entry.validate_finished_goods()

	assert (
		f"For quantity {work_order.qty * 10} should not be greater than work order quantity {work_order.qty}"
		in exc_info.value.args[0]
	)


@pytest.mark.order(33)
def test_validate_job_card():
	work_order = frappe.get_doc("Work Order", {"item_name": "Ambrosia Pie"})
	jc = frappe.get_doc(
		"Job Card", {"work_order": work_order.name, "operation": work_order.operations[0].operation}
	)
	jc.cancel()
	job_card = create_job_card(work_order, work_order.operations[0].as_dict(), auto_create=True)
	job_card.append(
		"time_logs",
		{
			"from_time": now(),
			"to_time": now(),
			"completed_qty": work_order.qty,
		},
	)
	job_card.save()
	assert job_card.validate_job_card() == None

	overproduction_percentage_for_work_order = frappe.db.get_value(
		"BOM", work_order.bom_no, "overproduction_percentage_for_work_order"
	)
	over_production_qty = work_order.qty * (1 + overproduction_percentage_for_work_order / 100)
	job_card.time_logs[0].completed_qty = over_production_qty
	job_card.save()

	assert job_card.validate_job_card() == None

	job_card.time_logs[0].completed_qty = over_production_qty + 10
	job_card.save()

	with pytest.raises(ValidationError) as exc_info:
		job_card.validate_job_card()

	assert (
		f"The Total Completed Qty ({over_production_qty + 10}) must be equal to Qty to Manufacture ({job_card.for_quantity})"
		in strip_html(exc_info.value.args[0])
	)
