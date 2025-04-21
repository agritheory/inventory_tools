# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe
from frappe.utils import safe_json_loads
from frappe.utils.data import nowdate
import numpy as np

from inventory_tools.inventory_tools.doctype.warehouse_plan.warehouse_plan import Grid_TSP

if TYPE_CHECKING:
	from erpnext.stock.doctype.pick_list_item.pick_list_item import PickListItem
	from erpnext.stock.doctype.pick_list.pick_list import PickList


class PathFinder:
	@staticmethod
	def _process_entries(item_code, qty, company, order_by, root_warehouse, to_date):
		# Retrieve stock ledger entries with the provided filters and ordering.
		sle = frappe.get_all(
			"Stock Ledger Entry",
			fields=["actual_qty", "posting_date", "creation", "warehouse"],
			filters={
				"item_code": item_code,
				"company": company,
				"posting_date": ["<=", to_date],
				"is_cancelled": 0,
				"actual_qty": [">", 0],
			},
			order_by=order_by,
		)

		newsle = []
		qty_obtained = 0

		# Process each entry until the required quantity is fulfilled.
		for entry in sle:
			# If a root warehouse is specified, ensure the entry belongs to it.
			if root_warehouse and get_root_warehouse(entry["warehouse"]) != root_warehouse:
				continue

			remaining_qty = qty - qty_obtained

			if entry["actual_qty"] > remaining_qty:
				newsle.append({"item_code": item_code, "warehouse": entry["warehouse"], "qty": remaining_qty})
				qty_obtained += remaining_qty
				break
			else:
				newsle.append(
					{"item_code": item_code, "warehouse": entry["warehouse"], "qty": entry["actual_qty"]}
				)
				qty_obtained += entry["actual_qty"]

		# If the accumulated quantity doesn't match the requested quantity, raise an error.
		if (qty - qty_obtained) != 0:
			raise frappe.ValidationError("Not enough items in root warehouse")
		return newsle

	@staticmethod
	def FIFO(item_code, qty, company, root_warehouse=None, to_date=None):
		# FIFO: Order by posting_date and creation in ascending order.
		if to_date is None:
			to_date = nowdate()
		return PathFinder._process_entries(
			item_code, qty, company, "posting_date, creation", root_warehouse, to_date
		)

	@staticmethod
	def LIFO(item_code, qty, company, root_warehouse=None, to_date=None):
		# LIFO: Order by posting_date and creation in descending order.
		if to_date is None:
			to_date = nowdate()
		return PathFinder._process_entries(
			item_code, qty, company, "posting_date desc, creation desc", root_warehouse, to_date
		)

	@staticmethod
	def deplete_max_bins(item_code, qty, company, root_warehouse=None, to_date=None):
		if to_date is None:
			to_date = nowdate()
		return PathFinder._process_entries(
			item_code, qty, company, "actual_qty, posting_date, creation", root_warehouse, to_date
		)

	@staticmethod
	def deplete_min_bins(item_code, qty, company, root_warehouse=None, to_date=None):
		if to_date is None:
			to_date = nowdate()
		return PathFinder._process_entries(
			item_code, qty, company, "actual_qty desc, posting_date, creation", root_warehouse, to_date
		)


def get_root_warehouse(warehouse):
	# Finds closest parent warehouse with a walkable floor plan; otherwise returns None
	wh_plans = [wh["name"] for wh in frappe.get_all("Warehouse Plan")]
	if warehouse in wh_plans:
		wp_doc = frappe.get_doc("Warehouse Plan", warehouse)
		if wp_doc.as_dict()["matrix"] is not None:
			return warehouse
	parent_warehouse = frappe.get_doc("Warehouse", warehouse).as_dict()["parent_warehouse"]
	if parent_warehouse == "":
		frappe.ValidationError("Warehouse does not have a parent warehouse")
		return None
	return get_root_warehouse(parent_warehouse)


@frappe.whitelist()
def optimize_route_picklist(item_whs: list, root_warehouse: str) -> list:
	"""Optimize the pick-up route for a list of items.

	This function takes a list of dictionaries, each representing an item along with its warehouse
	location, and returns the list reordered based on an optimized pick-up sequence.

	Expected format of `item_whs`:
	        [
	                {
	                        'item_code': <str>,   # The code identifying the item.
	                        'warehouse': <str>    # The warehouse where the item is located.
	                },
	                ...
	        ]

	Returns:
	        list: A reordered list of dictionaries, optimized for the pick-up route.
	"""

	# Grid
	grid = np.array(
		safe_json_loads(frappe.get_doc("Warehouse Plan", root_warehouse).as_dict()["matrix"])
	)

	# Scale
	imaginary_x = grid.shape[1]
	real_x = frappe.get_doc("Warehouse Plan", root_warehouse).as_dict()["horizontal"]
	scale = real_x / imaginary_x

	# Create the TSP solver instance.
	g = Grid_TSP(grid, scale=scale)

	root_wh = frappe.get_doc("Warehouse Plan", "All Warehouses - CFC").as_dict()
	dropoff = [g.pos2node((root_wh["pickup_point_x"], root_wh["pickup_point_y"]))]

	# Waypoints
	unique_whs = list({item_wh["warehouse"] for item_wh in item_whs})

	# Build a mapping from warehouse to its coordinate and node.
	warehouse_to_node = {}
	for wh in unique_whs:
		accessible_path = frappe.get_doc("Warehouse", wh).as_dict()["accessible_path"].split(",")
		coordinate = (int(accessible_path[0]), int(accessible_path[1]))
		warehouse_to_node[wh] = g.pos2node(coordinate)
	node_to_warehouse = {node: wh for wh, node in warehouse_to_node.items()}

	# For the TSP solver, create a list of nodes corresponding to each unique warehouse.
	pickup_list = list(warehouse_to_node.values())

	# Solve
	pickup_order, *rest = g.tsp(dropoff, pickup_list)

	# Map warehouse name to its order
	warehouse_order_map = {}
	for order_index, node in enumerate(pickup_order):
		wh = node_to_warehouse[node]
		warehouse_order_map[wh] = order_index

	# Sort original item_whs
	sorted_item_whs = sorted(
		item_whs,
		key=lambda item: (warehouse_order_map[item["warehouse"]], item["item_code"], item["qty"]),
	)
	return sorted_item_whs


@frappe.whitelist()
def optimize_path(doc: "PickList", strategy: str) -> list["PickListItem"]:
	"""Optimize the picklist route based on the specified strategy.

	Parameters:
	        doc (PickList or str):
	                The picklist document to optimize. The document must include:
	                        - "company".
	                        - "locations": A list of location dictionaries, each containing:
	                                - "item_code".
	                                - "qty".
	                                - "warehouse".
	        strategy (str):
	                The strategy to apply when determining the pick order. Supported strategies include:
	                        - "FIFO".
	                        - "LIFO".
	                        - "Deplete maximum number of Bins".
	                        - "Deplete minimum number of Bins".
	        Returns:
	                list[PickListItem]:
	                                A list of optimized picklist items generated based on the input strategy and common warehouse.

	        Raises:
	                frappe.ValidationError:
	                        If the locations in the picklist document do not all share the same root warehouse,
	                        indicating an inconsistency in the warehouse plan.
	"""
	if isinstance(doc, str):
		doc = frappe.get_doc("Pick List", doc).as_dict()
	# Extract item codes and root warehouses from document locations
	itemdict: dict[str, dict[str, float]] = {}
	for loc in doc["locations"]:
		code = loc["item_code"]
		qty = loc["qty"]
		if code in itemdict:
			itemdict[code]["qty"] += qty
		else:
			itemdict[code] = {"qty": qty}
	company = doc["company"]
	root_warehouses = [get_root_warehouse(loc["warehouse"]) for loc in doc["locations"]]

	# Ensure all locations share the same root warehouse
	if not all(wh == root_warehouses[0] for wh in root_warehouses):
		raise frappe.ValidationError("All items in pick list do not share a common warehouse plan")

	root_warehouse = root_warehouses[0]

	item_whs = []
	for item in itemdict.keys():
		if strategy == "FIFO":
			item_whs += PathFinder.FIFO(item, itemdict[item]["qty"], company, root_warehouse=root_warehouse)
		elif strategy == "LIFO":
			item_whs += PathFinder.LIFO(item, itemdict[item]["qty"], company, root_warehouse=root_warehouse)
		elif strategy == "Deplete maximum number of Bins":
			item_whs += PathFinder.deplete_max_bins(
				item, itemdict[item]["qty"], company, root_warehouse=root_warehouse
			)
		elif strategy == "Deplete minimum number of Bins":
			item_whs += PathFinder.deplete_min_bins(
				item, itemdict[item]["qty"], company, root_warehouse=root_warehouse
			)

	return optimize_route_picklist(item_whs, root_warehouse)
