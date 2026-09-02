# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import add_days, flt, nowdate


def run_warehouse_location_optimization(filters):
	return frappe.call(
		"frappe.desk.query_report.run",
		report_name="Warehouse Location Optimization",
		filters=filters,
		ignore_prepared_report=True,
	)


def make_material_transfer(item_code, s_warehouse, t_warehouse, qty=1):
	se = frappe.new_doc("Stock Entry")
	se.company = "Chelsea Fruit Co"
	se.stock_entry_type = "Material Transfer"
	se.append(
		"items",
		{
			"item_code": item_code,
			"s_warehouse": s_warehouse,
			"t_warehouse": t_warehouse,
			"qty": qty,
			"uom": frappe.db.get_value("Item", item_code, "stock_uom"),
			"stock_uom": frappe.db.get_value("Item", item_code, "stock_uom"),
			"conversion_factor": 1,
			"basic_rate": 1,
			"expense_account": frappe.get_value("Company", "Chelsea Fruit Co", "stock_adjustment_account"),
		},
	)
	se.save()
	se.submit()
	return se


@pytest.mark.order(70)
def test_report_returns_ranked_items_with_slot_suggestions():
	"""Chelsea Fruit Co plan shows heated items with suggested leaf slots and policy columns."""
	result = run_warehouse_location_optimization(
		{
			"company": "Chelsea Fruit Co",
			"warehouse_plan": "All Warehouses - CFC",
			"from_date": add_days(nowdate(), -365),
			"to_date": nowdate(),
		}
	)

	assert result["columns"]
	assert result["result"]

	first = result["result"][0]
	assert first["item_code"]
	assert first["heat"] > 0
	assert "qty_moved" in first
	assert "default_warehouse" in first
	assert "putaway_rule" in first
	assert "putaway_warehouse" in first
	assert "suggested_warehouse" in first
	assert "capacity" in first
	assert first["fit_status"] in {"fits", "unverified", "no_fit"}
	assert first["priority"] == 1


@pytest.mark.order(72)
def test_branch_filter_keeps_suggestions_inside_refrigerator_1():
	"""Scoping the report to Refrigerator 1 only suggests warehouses under that branch."""
	result = run_warehouse_location_optimization(
		{
			"company": "Chelsea Fruit Co",
			"warehouse_plan": "All Warehouses - CFC",
			"warehouse": "Refrigerator 1 - CFC",
			"from_date": add_days(nowdate(), -365),
			"to_date": nowdate(),
		}
	)

	branch_lft, branch_rgt = frappe.db.get_value("Warehouse", "Refrigerator 1 - CFC", ["lft", "rgt"])
	suggestions = [
		row["suggested_warehouse"] for row in result["result"] if row.get("suggested_warehouse")
	]
	assert suggestions
	assert "Fruit Storage 50 - CFC" not in suggestions

	for warehouse in suggestions:
		lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])
		assert branch_lft <= lft and rgt <= branch_rgt


@pytest.mark.order(74)
def test_material_transfer_increases_banana_heat_on_report():
	"""A Banana transfer inside Refrigerator 1 raises Banana's heat on the next report run."""
	filters = {
		"company": "Chelsea Fruit Co",
		"warehouse_plan": "All Warehouses - CFC",
		"warehouse": "Refrigerator 1 - CFC",
		"from_date": add_days(nowdate(), -30),
		"to_date": nowdate(),
	}
	before = run_warehouse_location_optimization(filters)
	before_heat = next(
		(row["heat"] for row in before["result"] if row["item_code"] == "Banana"),
		0,
	)

	make_material_transfer(
		"Banana",
		"Fruit Storage 11 - CFC",
		"Fruit Storage 2 - CFC",
		qty=1,
	)

	after = run_warehouse_location_optimization(filters)
	after_heat = next(row["heat"] for row in after["result"] if row["item_code"] == "Banana")
	assert after_heat == before_heat + 1


@pytest.mark.order(76)
def test_suggested_warehouses_are_leaf_storage_not_groups_or_transit():
	"""Suggested putaway targets are leaf storage locations, never groups or transit."""
	result = run_warehouse_location_optimization(
		{
			"company": "Chelsea Fruit Co",
			"warehouse_plan": "All Warehouses - CFC",
			"from_date": add_days(nowdate(), -365),
			"to_date": nowdate(),
		}
	)

	suggestions = {
		row["suggested_warehouse"] for row in result["result"] if row.get("suggested_warehouse")
	}
	assert suggestions

	for warehouse in suggestions:
		is_group, warehouse_type = frappe.db.get_value(
			"Warehouse", warehouse, ["is_group", "warehouse_type"]
		)
		assert not is_group
		assert warehouse_type != "Transit"


@pytest.mark.order(78)
def test_heat_rank_assigns_distinct_slots_to_top_items():
	"""Hotter items claim successive plan slots; the top two fitting items get different warehouses."""
	result = run_warehouse_location_optimization(
		{
			"company": "Chelsea Fruit Co",
			"warehouse_plan": "All Warehouses - CFC",
			"warehouse": "Refrigerator 1 - CFC",
			"from_date": add_days(nowdate(), -365),
			"to_date": nowdate(),
		}
	)

	with_slots = [
		row
		for row in result["result"]
		if row.get("suggested_warehouse") and row.get("fit_status") != "no_fit"
	]
	assert len(with_slots) >= 2
	assert with_slots[0]["priority"] < with_slots[1]["priority"]
	assert with_slots[0]["suggested_warehouse"] != with_slots[1]["suggested_warehouse"]
	assert with_slots[0]["heat"] >= with_slots[1]["heat"]


@pytest.mark.order(79)
def test_heat_rank_advances_cursor_past_skipped_no_fit_candidates(monkeypatch):
	"""After skipping no_fit slots, the next item starts after the assigned warehouse index."""
	from inventory_tools.warehouse_location_optimization import suggest_warehouse_by_heat_rank

	candidates = [
		{"name": "Fruit Storage 1 - CFC"},
		{"name": "Fruit Storage 2 - CFC"},
		{"name": "Fruit Storage 3 - CFC"},
		{"name": "Fruit Storage 4 - CFC"},
	]
	context = {"ordered_candidates": candidates, "pickup_x": 0.0, "pickup_y": 0.0}

	def mock_fits(item_code, warehouse):
		if warehouse in {"Fruit Storage 1 - CFC", "Fruit Storage 2 - CFC"}:
			return "no_fit"
		return "fits"

	monkeypatch.setattr(
		"inventory_tools.warehouse_location_optimization.item_fits_warehouse",
		mock_fits,
	)
	monkeypatch.setattr(
		"inventory_tools.warehouse_location_optimization.location_score",
		lambda item_code, warehouse, context: 1.0,
	)

	first_wh, _, _, cursor = suggest_warehouse_by_heat_rank("Banana", candidates, context, 0)
	assert first_wh == "Fruit Storage 3 - CFC"
	assert cursor == 3

	second_wh, _, _, next_cursor = suggest_warehouse_by_heat_rank(
		"Coconut", candidates, context, cursor
	)
	assert second_wh == "Fruit Storage 4 - CFC"
	assert next_cursor == 4


@pytest.mark.order(80)
def test_item_fits_warehouse_normalizes_item_and_warehouse_length_uom(monkeypatch):
	"""Exterior and interior dimensions in different length UOMs compare in meters."""
	from inventory_tools.warehouse_location_optimization import item_fits_warehouse

	length_uom = "Foot" if frappe.db.exists("UOM", "Foot") else "Meter"
	if length_uom == "Meter":
		item_length = 0.9
	else:
		item_length = 3

	def mock_item_dim(item_code, dimension_type, line_uom=None):
		return frappe._dict(
			item_length=item_length,
			item_width=item_length,
			item_height=1,
			item_volume=item_length**3,
			uom=length_uom,
			item_uom="Nos",
		)

	def mock_wh_dim(reference_doctype, reference_name, dimension_type):
		return frappe._dict(
			item_length=1.5,
			item_width=1.5,
			item_height=1,
			item_volume=2.25,
			uom="Meter",
		)

	monkeypatch.setattr(
		"inventory_tools.warehouse_location_optimization.resolve_item_physical_dimension",
		mock_item_dim,
	)
	monkeypatch.setattr(
		"inventory_tools.warehouse_location_optimization.get_physical_dimension",
		mock_wh_dim,
	)

	assert item_fits_warehouse("Banana", "Fruit Storage 1 - CFC") == "fits"


@pytest.mark.order(81)
def test_slot_capacity_is_physical_hold_not_qty_moved():
	"""When an item fits, Slot Capacity is how many units the bin holds — not Qty Moved."""
	result = run_warehouse_location_optimization(
		{
			"company": "Chelsea Fruit Co",
			"warehouse_plan": "All Warehouses - CFC",
			"from_date": add_days(nowdate(), -365),
			"to_date": nowdate(),
		}
	)

	fitting = [
		row
		for row in result["result"]
		if row.get("suggested_warehouse") and row.get("fit_status") == "fits"
	]
	assert fitting

	for row in fitting:
		assert flt(row["capacity"]) >= 1
		# Slot capacity is whole units from floor/volume packing, not period demand.
		assert flt(row["capacity"]) == int(flt(row["capacity"]))

	cranberry = next(
		(row for row in fitting if row["item_code"] == "Cranberry"),
		None,
	)
	if cranberry:
		# Cranberry exterior ~1.32×0.88 m in a typical 1.5×2.5 m Fruit Storage bin.
		assert flt(cranberry["capacity"]) in {2, 3}


@pytest.mark.order(82)
def test_set_default_warehouse_from_report_row():
	"""Apply Set Default Warehouse from a report row updates Banana's Chelsea Fruit Co default."""
	result = run_warehouse_location_optimization(
		{
			"company": "Chelsea Fruit Co",
			"warehouse_plan": "All Warehouses - CFC",
			"warehouse": "Refrigerator 1 - CFC",
			"from_date": add_days(nowdate(), -365),
			"to_date": nowdate(),
		}
	)
	row = next(
		report_row
		for report_row in result["result"]
		if report_row["item_code"] == "Banana" and report_row.get("suggested_warehouse")
	)

	original = frappe.db.get_value(
		"Item Default",
		{"parent": "Banana", "parenttype": "Item", "company": "Chelsea Fruit Co"},
		"default_warehouse",
	)

	frappe.call(
		"inventory_tools.inventory_tools.report.warehouse_location_optimization.warehouse_location_optimization.set_default_warehouses",
		rows=[
			{
				"item_code": "Banana",
				"suggested_warehouse": row["suggested_warehouse"],
			}
		],
		company="Chelsea Fruit Co",
	)

	assert (
		frappe.db.get_value(
			"Item Default",
			{"parent": "Banana", "parenttype": "Item", "company": "Chelsea Fruit Co"},
			"default_warehouse",
		)
		== row["suggested_warehouse"]
	)

	if original:
		frappe.call(
			"inventory_tools.inventory_tools.report.warehouse_location_optimization.warehouse_location_optimization.set_default_warehouses",
			rows=[{"item_code": "Banana", "suggested_warehouse": original}],
			company="Chelsea Fruit Co",
		)
	else:
		item = frappe.get_doc("Item", "Banana")
		item.set(
			"item_defaults",
			[
				item_default
				for item_default in item.item_defaults
				if item_default.company != "Chelsea Fruit Co"
			],
		)
		item.save()
