# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
import numpy as np
from frappe.utils import safe_json_loads

from inventory_tools.inventory_tools.doctype.warehouse_plan.warehouse_plan import Grid_TSP
from inventory_tools.inventory_tools.overrides.pick_list import (
	PathFinder,
	get_root_warehouse,
	optimize_route_picklist,
	optimize_path,
)

STRATEGY_WAREHOUSES = [
	{"item_code": "Cranberry", "qty": 2, "warehouse": "Fruit Storage 50 - CFC"},
	{"item_code": "Banana", "qty": 1, "warehouse": "Fruit Storage 1 - CFC"},
	{"item_code": "Coconut", "qty": 1, "warehouse": "Fruit Storage 10 - CFC"},
]


# --- Grid_TSP Tests ---


@pytest.mark.order(60)
def test_grid_tsp_graph_construction():
	"""Grid_TSP creates a connected graph from the warehouse plan matrix."""
	wp = frappe.get_doc("Warehouse Plan", "All Warehouses - CFC")
	grid = np.array(safe_json_loads(wp.matrix))
	g = Grid_TSP(grid, scale=1)

	assert g.G.number_of_nodes() > 0
	assert g.G.number_of_edges() > 0
	assert g.validate() is True


@pytest.mark.order(61)
def test_grid_tsp_pos2node_and_node2pos():
	"""Grid_TSP coordinate conversions are consistent."""
	wp = frappe.get_doc("Warehouse Plan", "All Warehouses - CFC")
	grid = np.array(safe_json_loads(wp.matrix))
	g = Grid_TSP(grid, scale=1)

	# Test a known walkable position (from fixture: pickup_point at 0,9)
	pos = (0, 9)
	node = g.pos2node(pos)
	# node2pos returns (row, col) which is (y, x)
	recovered = g.node2pos(node)
	assert recovered == (pos[1], pos[0])  # (row=y, col=x)


@pytest.mark.order(62)
def test_grid_tsp_find_path():
	"""Grid_TSP finds shortest path between two walkable nodes."""
	wp = frappe.get_doc("Warehouse Plan", "All Warehouses - CFC")
	grid = np.array(safe_json_loads(wp.matrix))
	g = Grid_TSP(grid, scale=1)

	# Use pickup point and a known accessible warehouse position
	start_pos = (wp.pickup_point_x, wp.pickup_point_y)
	start_node = g.pos2node(start_pos)

	# Get first warehouse with accessible_path
	wh = frappe.get_doc("Warehouse", "Fruit Storage 1 - CFC")
	accessible = wh.accessible_path.split(",")
	end_pos = (int(accessible[0]), int(accessible[1]))
	end_node = g.pos2node(end_pos)

	path, distance = g.find_path(start_node, end_node)

	assert len(path) > 0
	assert path[0] == start_node
	assert path[-1] == end_node
	assert distance > 0


@pytest.mark.order(63)
def test_grid_tsp_tsp_optimization():
	"""Grid_TSP solves TSP for multiple pickup locations."""
	wp = frappe.get_doc("Warehouse Plan", "All Warehouses - CFC")
	grid = np.array(safe_json_loads(wp.matrix))
	g = Grid_TSP(grid, scale=wp.horizontal / grid.shape[1])

	pickup_point = [g.pos2node((wp.pickup_point_x, wp.pickup_point_y))]

	# Get a few warehouse accessible positions
	warehouse_nodes = []
	for wh_name in ["Fruit Storage 1 - CFC", "Fruit Storage 10 - CFC", "Fruit Storage 20 - CFC"]:
		wh = frappe.get_doc("Warehouse", wh_name)
		accessible = wh.accessible_path.split(",")
		node = g.pos2node((int(accessible[0]), int(accessible[1])))
		warehouse_nodes.append(node)

	pickup_order, _, _ = g.tsp(pickup_point, warehouse_nodes)

	assert len(pickup_order) == len(warehouse_nodes)
	assert set(pickup_order) == set(warehouse_nodes)


# --- PathFinder Tests ---


@pytest.mark.order(64)
def test_pathfinder_fifo():
	"""PathFinder.FIFO returns stock from oldest entries first."""
	# Find an item with stock in CFC warehouses
	item_code = "Cranberry"
	company = "Chelsea Fruit Co"

	# Get stock ledger entries to verify FIFO ordering
	sle = frappe.get_all(
		"Stock Ledger Entry",
		fields=["posting_date", "warehouse", "actual_qty"],
		filters={
			"item_code": item_code,
			"company": company,
			"is_cancelled": 0,
			"actual_qty": [">", 0],
		},
		order_by="posting_date, creation",
	)

	if not sle:
		pytest.skip(f"No stock ledger entries for {item_code}")

	total_qty = sum(s.actual_qty for s in sle)
	result = PathFinder.FIFO(item_code, min(total_qty, 10), company)

	assert len(result) > 0
	assert all(r["item_code"] == item_code for r in result)
	assert sum(r["qty"] for r in result) == min(total_qty, 10)

	# First result should be from oldest entry
	if len(sle) > 1:
		oldest_date = min(s.posting_date for s in sle)
		assert result[0]["warehouse"] in [s.warehouse for s in sle if s.posting_date == oldest_date]


@pytest.mark.order(65)
def test_pathfinder_lifo():
	"""PathFinder.LIFO returns stock from newest entries first."""
	item_code = "Cranberry"
	company = "Chelsea Fruit Co"

	sle = frappe.get_all(
		"Stock Ledger Entry",
		fields=["posting_date", "warehouse", "actual_qty"],
		filters={
			"item_code": item_code,
			"company": company,
			"is_cancelled": 0,
			"actual_qty": [">", 0],
		},
		order_by="posting_date desc, creation desc",
	)

	if not sle:
		pytest.skip(f"No stock ledger entries for {item_code}")

	total_qty = sum(s.actual_qty for s in sle)
	result = PathFinder.LIFO(item_code, min(total_qty, 10), company)

	assert len(result) > 0
	assert sum(r["qty"] for r in result) == min(total_qty, 10)

	# First result should be from newest entry
	if len(sle) > 1:
		newest_date = max(s.posting_date for s in sle)
		assert result[0]["warehouse"] in [s.warehouse for s in sle if s.posting_date == newest_date]


@pytest.mark.order(66)
def test_pathfinder_deplete_max_bins():
	"""PathFinder.deplete_max_bins prefers smaller quantity bins."""
	item_code = "Cranberry"
	company = "Chelsea Fruit Co"

	sle = frappe.get_all(
		"Stock Ledger Entry",
		fields=["posting_date", "warehouse", "actual_qty"],
		filters={
			"item_code": item_code,
			"company": company,
			"is_cancelled": 0,
			"actual_qty": [">", 0],
		},
		order_by="actual_qty, posting_date, creation",
	)

	if not sle:
		pytest.skip(f"No stock ledger entries for {item_code}")

	total_qty = sum(s.actual_qty for s in sle)
	result = PathFinder.deplete_max_bins(item_code, min(total_qty, 10), company)

	assert len(result) > 0
	assert sum(r["qty"] for r in result) == min(total_qty, 10)


@pytest.mark.order(67)
def test_pathfinder_deplete_min_bins():
	"""PathFinder.deplete_min_bins prefers larger quantity bins."""
	item_code = "Cranberry"
	company = "Chelsea Fruit Co"

	sle = frappe.get_all(
		"Stock Ledger Entry",
		fields=["posting_date", "warehouse", "actual_qty"],
		filters={
			"item_code": item_code,
			"company": company,
			"is_cancelled": 0,
			"actual_qty": [">", 0],
		},
		order_by="actual_qty desc, posting_date, creation",
	)

	if not sle:
		pytest.skip(f"No stock ledger entries for {item_code}")

	total_qty = sum(s.actual_qty for s in sle)
	result = PathFinder.deplete_min_bins(item_code, min(total_qty, 10), company)

	assert len(result) > 0
	assert sum(r["qty"] for r in result) == min(total_qty, 10)


@pytest.mark.order(68)
def test_pathfinder_insufficient_stock_raises():
	"""PathFinder raises ValidationError when stock is insufficient."""
	item_code = "Cranberry"
	company = "Chelsea Fruit Co"

	with pytest.raises(frappe.ValidationError, match="Not enough items"):
		PathFinder.FIFO(item_code, 999999, company)


# --- Route Optimization Tests ---


@pytest.mark.order(69)
def test_get_root_warehouse():
	"""get_root_warehouse finds parent warehouse with Warehouse Plan."""
	# Fruit Storage warehouses are children of All Warehouses - CFC which has a plan
	root = get_root_warehouse("Fruit Storage 1 - CFC")
	assert root == "All Warehouses - CFC"


@pytest.mark.order(70)
def test_optimize_route_picklist():
	"""optimize_route_picklist reorders items by shortest walking path."""
	root_warehouse = "All Warehouses - CFC"

	# Create item list from different warehouse locations (using actual fixture items)
	item_whs = [
		{"item_code": "Banana", "warehouse": "Fruit Storage 1 - CFC", "qty": 5},
		{"item_code": "Coconut", "warehouse": "Fruit Storage 50 - CFC", "qty": 3},
		{"item_code": "Cranberry", "warehouse": "Fruit Storage 10 - CFC", "qty": 2},
	]

	result = optimize_route_picklist(item_whs, root_warehouse)

	assert len(result) == len(item_whs)
	# All items should be present
	assert {r["item_code"] for r in result} == {i["item_code"] for i in item_whs}


# --- Pick List Integration Tests ---


@pytest.mark.order(71)
def test_optimize_path_fifo():
	"""optimize_path with FIFO strategy returns optimized pick list."""
	pick_list = {
		"company": "Chelsea Fruit Co",
		"locations": [
			{"item_code": "Cranberry", "qty": 5, "warehouse": "Fruit Storage 10 - CFC"},
		],
	}

	result = optimize_path(pick_list, "FIFO")

	assert len(result) > 0
	assert all("item_code" in r for r in result)
	assert all("warehouse" in r for r in result)
	assert all("qty" in r for r in result)
	total_qty = sum(r["qty"] for r in result)
	assert total_qty == 5


@pytest.mark.order(72)
def test_optimize_path_lifo():
	"""optimize_path with LIFO strategy returns optimized pick list."""
	pick_list = {
		"company": "Chelsea Fruit Co",
		"locations": [
			{"item_code": "Cranberry", "qty": 5, "warehouse": "Fruit Storage 10 - CFC"},
		],
	}

	result = optimize_path(pick_list, "LIFO")

	assert len(result) > 0
	total_qty = sum(r["qty"] for r in result)
	assert total_qty == 5


@pytest.mark.order(73)
def test_optimize_path_deplete_max_bins():
	"""optimize_path with Deplete maximum number of Bins strategy."""
	pick_list = {
		"company": "Chelsea Fruit Co",
		"locations": [
			{"item_code": "Cranberry", "qty": 5, "warehouse": "Fruit Storage 10 - CFC"},
		],
	}

	result = optimize_path(pick_list, "Deplete maximum number of Bins")

	assert len(result) > 0
	total_qty = sum(r["qty"] for r in result)
	assert total_qty == 5


@pytest.mark.order(74)
def test_optimize_path_deplete_min_bins():
	"""optimize_path with Deplete minimum number of Bins strategy."""
	pick_list = {
		"company": "Chelsea Fruit Co",
		"locations": [
			{"item_code": "Cranberry", "qty": 5, "warehouse": "Fruit Storage 10 - CFC"},
		],
	}

	result = optimize_path(pick_list, "Deplete minimum number of Bins")

	assert len(result) > 0
	total_qty = sum(r["qty"] for r in result)
	assert total_qty == 5


# --- InventoryToolsPickList.after_mapping Tests ---


@pytest.mark.order(75)
def test_after_mapping_optimizes_with_default_strategy():
	"""after_mapping reorders locations using the company's default strategy."""
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	original_strategy = settings.default_route_optimization_strategy
	settings.default_route_optimization_strategy = "FIFO"
	settings.save()

	try:
		pl = frappe.new_doc("Pick List")
		pl.company = "Chelsea Fruit Co"
		for loc in STRATEGY_WAREHOUSES:
			pl.append("locations", loc)

		pl.after_mapping(None)

		expected = optimize_path(
			{"company": "Chelsea Fruit Co", "locations": STRATEGY_WAREHOUSES},
			"FIFO",
		)
		assert [loc.warehouse for loc in pl.locations] == [r["warehouse"] for r in expected]
	finally:
		settings.default_route_optimization_strategy = original_strategy
		settings.save()


@pytest.mark.order(76)
def test_after_mapping_is_noop_with_source_document_order():
	"""after_mapping leaves locations unchanged when strategy is Use Source Document Order."""
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	original_strategy = settings.default_route_optimization_strategy
	settings.default_route_optimization_strategy = "Use Source Document Order"
	settings.save()

	try:
		pl = frappe.new_doc("Pick List")
		pl.company = "Chelsea Fruit Co"
		for loc in STRATEGY_WAREHOUSES:
			pl.append("locations", loc)

		original_order = [loc["warehouse"] for loc in STRATEGY_WAREHOUSES]
		pl.after_mapping(None)

		assert [loc.warehouse for loc in pl.locations] == original_order
	finally:
		settings.default_route_optimization_strategy = original_strategy
		settings.save()


@pytest.mark.order(77)
def test_after_mapping_populates_onload_data():
	"""after_mapping sets __onload.default_route_optimization_strategy for the frontend dialog."""
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	original_strategy = settings.default_route_optimization_strategy
	settings.default_route_optimization_strategy = "LIFO"
	settings.save()

	try:
		pl = frappe.new_doc("Pick List")
		pl.company = "Chelsea Fruit Co"
		pl.append("locations", STRATEGY_WAREHOUSES[0])

		pl.after_mapping(None)

		assert pl.get_onload("default_route_optimization_strategy") == "LIFO"
	finally:
		settings.default_route_optimization_strategy = original_strategy
		settings.save()


@pytest.mark.order(78)
def test_after_mapping_is_noop_without_company():
	"""after_mapping does nothing when company is not set on the document."""
	pl = frappe.new_doc("Pick List")
	for loc in STRATEGY_WAREHOUSES:
		pl.append("locations", loc)

	original_order = [loc["warehouse"] for loc in STRATEGY_WAREHOUSES]
	pl.after_mapping(None)

	assert [loc.warehouse for loc in pl.locations] == original_order
