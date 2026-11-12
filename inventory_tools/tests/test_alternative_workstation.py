# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry, make_work_order
from frappe.utils import flt

from inventory_tools.inventory_tools.overrides.workstation import (
	get_alternative_workstations,
	resolve_alternative_workstation_names,
	working_hour_spans,
	working_hours_overlap,
)

# Kept separate from Refrigerated Display - APC so these receipts don't move the
# Ambrosia Pie valuation rate that test_alternative_sales_workflow asserts on.
BACKFLUSH_FG_WAREHOUSE = "Bakery Display - APC"


def submit_all_purchase_receipts():
	for pr in frappe.get_all("Purchase Receipt", {"docstatus": 0}):
		doc = frappe.get_doc("Purchase Receipt", pr)
		doc.submit()


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


def receive_raw_materials(se_dict, work_order_name):
	wo = frappe.get_doc("Work Order", work_order_name)
	bom_rates = {r.item_code: flt(r.rate) for r in wo.required_items}
	receipt = frappe.get_doc(**se_dict)
	receipt.stock_entry_type = "Material Receipt"
	receipt.purpose = "Material Receipt"
	for row in receipt.items:
		row.t_warehouse = row.s_warehouse
		row.s_warehouse = None
		row.expense_account = "5119 - Stock Adjustment - APC"
		row.basic_rate = (
			flt(
				frappe.db.get_value(
					"Item Price",
					{"item_code": row.item_code, "price_list": "Bakery Buying", "buying": 1},
					"price_list_rate",
				)
			)
			or bom_rates.get(row.item_code)
			or flt(frappe.db.get_value("Item", row.item_code, "valuation_rate"))
		)
		assert row.basic_rate > 0, f"No valuation source for {row.item_code}"
	receipt.insert()
	receipt.submit()


def transfer_raw_materials_to_wip(work_order_name, qty):
	se_dict = make_stock_entry(work_order_name, "Material Transfer for Manufacture", qty)
	receive_raw_materials(se_dict, work_order_name)
	se = frappe.get_doc(**se_dict)
	se.save()
	se.submit()
	return se


def create_submitted_ambrosia_pie_work_order(qty, company="Ambrosia Pie Company"):
	bom = frappe.db.get_value(
		"BOM",
		{"item": "Ambrosia Pie", "is_default": 1, "docstatus": 1},
		"name",
	)
	assert bom, "Default Ambrosia Pie BOM missing in test data"
	wo = make_work_order(bom, "Ambrosia Pie", qty=qty, company=company)
	wo.wip_warehouse = "Kitchen - APC"
	wo.fg_warehouse = BACKFLUSH_FG_WAREHOUSE
	wo.insert()
	wo.submit()
	return wo.name


from inventory_tools.inventory_tools.overrides.workstation import (
	working_hour_spans,
	working_hours_overlap,
)


@pytest.mark.order(26)
def test_alternative_workstation_query():
	response = frappe.call(
		"frappe.desk.search.search_link",
		**{
			"doctype": "Workstation",
			"txt": "",
			"reference_doctype": "Job Card",
		},
	)
	assert len(response) == 10
	inventory_tools_settings = frappe.get_doc(
		"Inventory Tools Settings", frappe.defaults.get_defaults().get("company")
	)
	inventory_tools_settings.allow_alternative_workstations = (
		"Allow Manually Defined Alternative Workstations"
	)
	inventory_tools_settings.save()
	response = frappe.call(
		"frappe.desk.search.search_link",
		**{
			"doctype": "Workstation",
			"txt": "",
			"query": "inventory_tools.inventory_tools.overrides.workstation.get_alternative_workstations",
			"filters": {"operation": "Gather Pie Filling Ingredients"},
			"reference_doctype": "Job Card",
		},
	)
	assert len(response) == 2
	assert response[0].get("value") == "Food Prep Table 1"
	assert "Default" in response[0].get("description")
	assert response[1].get("value") == "Food Prep Table 2"


@pytest.mark.order(27)
def test_alternative_workstation_by_type_query():
	response = frappe.call(
		"frappe.desk.search.search_link",
		**{
			"doctype": "Workstation",
			"txt": "",
			"reference_doctype": "Job Card",
		},
	)
	assert len(response) == 10

	inventory_tools_settings = frappe.get_doc(
		"Inventory Tools Settings", frappe.defaults.get_defaults().get("company")
	)
	inventory_tools_settings.allow_alternative_workstations = (
		"Allow Alternative Workstations Based on Workstation Type"
	)
	inventory_tools_settings.save()

	response = frappe.call(
		"frappe.desk.search.search_link",
		**{
			"doctype": "Workstation",
			"txt": "",
			"query": "inventory_tools.inventory_tools.overrides.workstation.get_alternative_workstations",
			"filters": {"operation": "Gather Pie Filling Ingredients"},
			"reference_doctype": "Job Card",
		},
	)

	assert len(response) >= 2
	workstation_values = [r.get("value") for r in response]
	assert "Food Prep Table 1" in workstation_values
	assert "Food Prep Table 2" in workstation_values


@pytest.mark.order(28)
def test_workstation_availability_page_respects_settings():
	from inventory_tools.inventory_tools.page.alternative_workstation import (
		get_workstation_availability,
	)

	work_order_name = frappe.db.get_value(
		"Work Order",
		{"item_name": "Ambrosia Pie", "docstatus": 1, "status": ("!=", "Completed")},
		"name",
	)
	assert work_order_name, "No submitted open Ambrosia Pie Work Order in test data"

	company = frappe.db.get_value("Work Order", work_order_name, "company")
	inventory_tools_settings = frappe.get_doc("Inventory Tools Settings", company)
	original_setting = inventory_tools_settings.allow_alternative_workstations

	try:
		inventory_tools_settings.allow_alternative_workstations = "Do Not Allow Alternative Workstations"
		inventory_tools_settings.save()

		data = get_workstation_availability(work_order_name)
		assert data
		for operation in data:
			assert operation["alternatives"] == []

		inventory_tools_settings.allow_alternative_workstations = (
			"Allow Alternative Workstations Based on Workstation Type"
		)
		inventory_tools_settings.save()

		data = get_workstation_availability(work_order_name)
		assemble_op = next((op for op in data if op["operation"] == "Assemble Pie Op"), None)
		assert assemble_op, "Assemble Pie Op missing on Ambrosia Pie Work Order"
		assert not assemble_op["is_completed"]
		alt_names = {alt["workstation"] for alt in assemble_op["alternatives"]}
		assert "Food Prep Table 1" in alt_names
		assert "Assemble Pie Station" not in alt_names

		inventory_tools_settings.allow_alternative_workstations = (
			"Allow Manually Defined Alternative Workstations"
		)
		inventory_tools_settings.save()

		data = get_workstation_availability(work_order_name)
		assemble_op = next((op for op in data if op["operation"] == "Assemble Pie Op"), None)
		assert assemble_op
		assemble_alts = {alt["workstation"] for alt in assemble_op["alternatives"]}
		assert "Food Prep Table 1" in assemble_alts
		assert "Assemble Pie Station" not in assemble_alts
	finally:
		inventory_tools_settings.allow_alternative_workstations = original_setting
		inventory_tools_settings.save()


@pytest.mark.order(29)
def test_assign_workstation_on_submitted_work_order():
	from inventory_tools.inventory_tools.page.alternative_workstation import assign_workstation

	work_order_name = frappe.db.get_value(
		"Work Order",
		{"item_name": "Ambrosia Pie", "docstatus": 1, "status": ("!=", "Completed")},
		"name",
	)
	assert work_order_name

	wo = frappe.get_doc("Work Order", work_order_name)
	operation_row = next((op for op in wo.operations if op.operation == "Assemble Pie Op"), None)
	assert operation_row, "Assemble Pie Op missing on Ambrosia Pie Work Order"

	company = wo.company
	inventory_tools_settings = frappe.get_doc("Inventory Tools Settings", company)
	original_setting = inventory_tools_settings.allow_alternative_workstations
	original_workstation = operation_row.workstation
	operation_name = operation_row.operation

	try:
		inventory_tools_settings.allow_alternative_workstations = (
			"Allow Manually Defined Alternative Workstations"
		)
		inventory_tools_settings.save()

		alternatives = resolve_alternative_workstation_names(
			operation_name, company, original_workstation
		)
		assert original_workstation == "Food Prep Table 2"
		assert "Food Prep Table 1" in alternatives
		assert "Assemble Pie Station" not in alternatives
		new_workstation = "Food Prep Table 1"

		session_user = frappe.session.user
		frappe.set_user("Guest")
		try:
			with pytest.raises(frappe.PermissionError):
				assign_workstation(work_order_name, operation_name, new_workstation)
		finally:
			frappe.set_user(session_user)
		assert frappe.db.get_value("Work Order Operation", operation_row.name, "workstation") == (
			original_workstation
		)

		result = assign_workstation(work_order_name, operation_name, new_workstation)
		assert result["status"] == "success"

		wo.reload()
		updated = next(op for op in wo.operations if op.operation == operation_name)
		assert updated.workstation == new_workstation
	finally:
		assign_workstation(work_order_name, operation_name, original_workstation)
		inventory_tools_settings.allow_alternative_workstations = original_setting
		inventory_tools_settings.save()


@pytest.mark.order(30)
def test_same_warehouse_filtering_and_enforcement():
	from inventory_tools.inventory_tools.page.alternative_workstation import assign_workstation

	company = "Ambrosia Pie Company"
	assert frappe.db.get_value("Workstation", "Food Prep Table 1", "warehouse") == "Kitchen - APC"
	assert (
		frappe.db.get_value("Workstation", "Assemble Pie Station", "warehouse") == "Storeroom - APC"
	)

	names = resolve_alternative_workstation_names("Assemble Pie Op", company, "Food Prep Table 2")
	assert "Food Prep Table 1" in names
	assert "Assemble Pie Station" not in names

	rows = get_alternative_workstations(
		"Workstation",
		"",
		"name",
		0,
		20,
		{"operation": "Assemble Pie Op", "company": company},
	)
	values = {r[0] for r in rows}
	assert "Food Prep Table 1" in values
	assert "Assemble Pie Station" not in values

	work_order_name = frappe.db.get_value(
		"Work Order",
		{"item_name": "Ambrosia Pie", "docstatus": 1, "status": ("!=", "Completed")},
		"name",
	)
	assert work_order_name
	wo_before = frappe.get_doc("Work Order", work_order_name)
	op_row = next((op for op in wo_before.operations if op.operation == "Assemble Pie Op"), None)
	assert op_row
	orig_ws = op_row.workstation

	with pytest.raises(frappe.ValidationError):
		assign_workstation(work_order_name, "Assemble Pie Op", "Assemble Pie Station")

	wo_after = frappe.get_doc("Work Order", work_order_name)
	still = next(op for op in wo_after.operations if op.operation == "Assemble Pie Op")
	assert still.workstation == orig_ws

	jc_name = frappe.db.get_value(
		"Job Card",
		{"work_order": work_order_name, "operation": "Assemble Pie Op", "docstatus": 0},
		"name",
	)
	assert jc_name, "Draft Assemble Pie Op Job Card expected in test data"
	jc = frappe.get_doc("Job Card", jc_name)
	orig_jc_ws = jc.workstation

	with pytest.raises(frappe.ValidationError):
		jc.workstation = "Assemble Pie Station"
		jc.save()

	jc.reload()
	assert jc.workstation == orig_jc_ws

	jc.workstation = "Food Prep Table 1"
	jc.save()
	jc.reload()
	assert jc.workstation == "Food Prep Table 1"

	jc.workstation = orig_jc_ws
	jc.save()

	inventory_tools_settings = frappe.get_doc("Inventory Tools Settings", company)
	original_setting = inventory_tools_settings.allow_alternative_workstations
	try:
		inventory_tools_settings.allow_alternative_workstations = "Do Not Allow Alternative Workstations"
		inventory_tools_settings.save()
		jc.reload()
		jc.workstation = "Assemble Pie Station"
		jc.save()
		jc.reload()
		assert jc.workstation == "Assemble Pie Station"
		jc.workstation = orig_jc_ws
		jc.save()
	finally:
		inventory_tools_settings.allow_alternative_workstations = original_setting
		inventory_tools_settings.save()


@pytest.mark.order(31)
def test_backflush_after_alternative_workstation_transferred_mode():
	"""
	Manufacture consumes raw materials from WIP after swapping to a compatible workstation.

	| Account (type)              | Debit | Credit |
	| --------------------------- | ----- | ------ |
	| Finished goods (asset)      |   X   |        |
	| Work in Progress 1420       |       |   X    |
	"""
	mfg = frappe.get_doc("Manufacturing Settings", "Manufacturing Settings")
	prev_backflush = mfg.backflush_raw_materials_based_on
	prev_consumption = mfg.material_consumption
	mfg.backflush_raw_materials_based_on = "Material Transferred for Manufacture"
	mfg.material_consumption = 1
	mfg.save()

	qty = 7.0
	try:
		submit_all_purchase_receipts()
		wo = create_submitted_ambrosia_pie_work_order(qty)

		transfer_raw_materials_to_wip(wo, qty)

		from inventory_tools.inventory_tools.page.alternative_workstation import assign_workstation

		assign_workstation(wo, "Assemble Pie Op", "Food Prep Table 1")

		complete_job_cards_for_work_order(wo)
		assert_completed_operation_locked(wo, "Assemble Pie Op", "Food Prep Table 1")

		sem_dict = make_stock_entry(wo, "Manufacture", qty)
		sem = frappe.get_doc(**sem_dict)
		sem.save()
		sem.submit()

		assert_manufacture_backflush(wo, sem.name, qty)
	finally:
		mfg.backflush_raw_materials_based_on = prev_backflush
		mfg.material_consumption = prev_consumption
		mfg.save()


def assert_completed_operation_locked(work_order_name, operation, workstation):
	"""Completed operations are reported as such and can't be reassigned."""
	from inventory_tools.inventory_tools.page.alternative_workstation import (
		assign_workstation,
		get_workstation_availability,
	)

	data = get_workstation_availability(work_order_name)
	op_data = next(op for op in data if op["operation"] == operation)
	assert op_data["is_completed"]
	assert op_data["workstation"] == workstation
	assert op_data["alternatives"], "Alternatives should still be listed (disabled in the UI)"
	alternative = op_data["alternatives"][0]["workstation"]

	with pytest.raises(frappe.ValidationError):
		assign_workstation(work_order_name, operation, alternative)

	wo = frappe.get_doc("Work Order", work_order_name)
	assert next(op for op in wo.operations if op.operation == operation).workstation == workstation
	for jc_workstation in frappe.get_all(
		"Job Card",
		{"work_order": work_order_name, "operation": operation, "docstatus": 1},
		pluck="workstation",
	):
		assert jc_workstation == workstation


@pytest.mark.order(32)
def test_backflush_after_alternative_workstation_bom_with_consumption():
	"""
	BOM mode with material consumption pulls unconsumed RM from WIP after workstation swap.

	| Account (type)              | Debit | Credit |
	| --------------------------- | ----- | ------ |
	| Finished goods (asset)      |   X   |        |
	| Work in Progress 1420       |       |   X    |
	"""
	mfg = frappe.get_doc("Manufacturing Settings", "Manufacturing Settings")
	prev_backflush = mfg.backflush_raw_materials_based_on
	prev_consumption = mfg.material_consumption
	mfg.backflush_raw_materials_based_on = "BOM"
	mfg.material_consumption = 1
	mfg.save()

	qty = 8.0
	try:
		submit_all_purchase_receipts()
		wo = create_submitted_ambrosia_pie_work_order(qty)

		transfer_raw_materials_to_wip(wo, qty)

		from inventory_tools.inventory_tools.page.alternative_workstation import assign_workstation

		assign_workstation(wo, "Assemble Pie Op", "Food Prep Table 1")

		complete_job_cards_for_work_order(wo)

		sem_dict = make_stock_entry(wo, "Manufacture", qty)
		sem = frappe.get_doc(**sem_dict)
		sem.save()
		sem.submit()

		assert_manufacture_backflush(wo, sem.name, qty)
	finally:
		mfg.backflush_raw_materials_based_on = prev_backflush
		mfg.material_consumption = prev_consumption
		mfg.save()


@pytest.mark.order(33)
def test_backflush_after_alternative_workstation_bom_without_consumption():
	"""
	BOM mode without separate consumption entries still consumes from WIP.

	| Account (type)              | Debit | Credit |
	| --------------------------- | ----- | ------ |
	| Finished goods (asset)      |   X   |        |
	| Work in Progress 1420       |       |   X    |
	"""
	mfg = frappe.get_doc("Manufacturing Settings", "Manufacturing Settings")
	prev_backflush = mfg.backflush_raw_materials_based_on
	prev_consumption = mfg.material_consumption
	mfg.backflush_raw_materials_based_on = "BOM"
	mfg.material_consumption = 0
	mfg.save()

	qty = 9.0
	try:
		submit_all_purchase_receipts()
		wo = create_submitted_ambrosia_pie_work_order(qty)

		transfer_raw_materials_to_wip(wo, qty)

		from inventory_tools.inventory_tools.page.alternative_workstation import assign_workstation

		assign_workstation(wo, "Assemble Pie Op", "Food Prep Table 1")

		complete_job_cards_for_work_order(wo)

		sem_dict = make_stock_entry(wo, "Manufacture", qty)
		sem = frappe.get_doc(**sem_dict)
		sem.save()
		sem.submit()

		assert_manufacture_backflush(wo, sem.name, qty)
	finally:
		mfg.backflush_raw_materials_based_on = prev_backflush
		mfg.material_consumption = prev_consumption
		mfg.save()


def assert_manufacture_backflush(work_order_name, manufacture_se_name, qty):
	wo = frappe.get_doc("Work Order", work_order_name)
	assert flt(wo.produced_qty) == flt(qty)
	assert wo.status == "Completed"

	wip = "Kitchen - APC"
	fg_wh = BACKFLUSH_FG_WAREHOUSE

	for row in wo.required_items:
		assert flt(row.transferred_qty) == flt(row.consumed_qty)

	sem = frappe.get_doc("Stock Entry", manufacture_se_name)
	for row in sem.items:
		if row.is_finished_item:
			assert row.t_warehouse == fg_wh
			continue
		assert row.s_warehouse == wip
		assert flt(row.qty) > 0

	bom = frappe.get_cached_doc("BOM", wo.bom_no)
	by_item = {r.item_code: r for r in bom.items}
	for row in sem.items:
		if row.is_finished_item:
			continue
		bom_row = by_item.get(row.item_code)
		assert bom_row is not None
		expected = flt(bom_row.qty) / flt(bom.quantity) * flt(qty)
		assert flt(row.qty, 3) == flt(expected, 3)

	sle = frappe.get_all(
		"Stock Ledger Entry",
		filters={"voucher_type": "Stock Entry", "voucher_no": manufacture_se_name},
		fields=["item_code", "warehouse", "stock_value_difference", "actual_qty"],
	)
	wip_credit = sum(
		flt(r.stock_value_difference)
		for r in sle
		if r.warehouse == wip and flt(r.actual_qty) < 0 and r.item_code != wo.production_item
	)
	assert wip_credit < 0
	fg_rows = [r for r in sle if r.warehouse == fg_wh and r.item_code == wo.production_item]
	assert fg_rows
	assert sum(flt(r.actual_qty) for r in fg_rows) > 0

	gl = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": "Stock Entry", "voucher_no": manufacture_se_name},
		fields=["debit", "credit"],
	)
	assert flt(sum(r.debit for r in gl), 2) == flt(sum(r.credit for r in gl), 2)
	wip_entries = [
		e
		for e in frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Stock Entry", "voucher_no": manufacture_se_name},
			fields=["account", "debit", "credit"],
		)
		if "1420" in e.account and "Work in Progress" in e.account
	]
	assert wip_entries
	assert sum(flt(e.credit) for e in wip_entries) > 0


@pytest.mark.order(45)
def test_overnight_working_hours_overlap_on_48_hour_clock():
	"""A shift that crosses midnight overlaps a morning shift on the next day."""
	overnight = working_hour_spans("22:00:00", "06:00:00")
	morning = working_hour_spans("05:00:00", "07:00:00")
	assert working_hours_overlap(overnight, morning)

	later_that_morning = working_hour_spans("07:00:00", "08:00:00")
	assert not working_hours_overlap(overnight, later_that_morning)

	starts_when_overnight_ends = working_hour_spans("06:00:00", "08:00:00")
	assert not working_hours_overlap(overnight, starts_when_overnight_ends)

	day = working_hour_spans("09:00:00", "17:00:00")
	late_afternoon = working_hour_spans("16:00:00", "18:00:00")
	assert working_hours_overlap(day, late_afternoon)
