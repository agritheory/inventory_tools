from typing import TYPE_CHECKING

import frappe
from frappe.utils import safe_json_loads
from frappe.utils.data import nowdate
import numpy as np

from inventory_tools.inventory_tools.doctype.warehouse_plan.warehouse_plan import Grid_TSP

if TYPE_CHECKING:
	from erpnext.stock.doctype.pick_list_item.pick_list_item import PickListItem
	from erpnext.stock.doctype.pick_list.pick_list import PickList


@frappe.whitelist()
def optimize_path(doc: "PickList", strategy: str) -> list["PickListItem"]:
	doc = safe_json_loads(doc) if isinstance(doc, str) else doc
	return doc.locations
	# returns a list of Pick List Item in the correct order

	@staticmethod
	def deplete_max_bins(item_code, qty, company, root_warehouse=None, to_date=None):
		if to_date is None:
			to_date = nowdate()
		return Rules._process_entries(
			item_code, qty, company, "actual_qty, posting_date, creation", root_warehouse, to_date
		)

	@staticmethod
	def deplete_min_bins(item_code, qty, company, root_warehouse=None, to_date=None):
		if to_date is None:
			to_date = nowdate()
		return Rules._process_entries(
			item_code, qty, company, "actual_qty desc, posting_date, creation", root_warehouse, to_date
		)


def validate_warehouse_has_plan(items):
	warehouses = []
	for item in items:
		item_list = {}
		item_list["item"] = item
		root_warehouse = []
		item_warehouses = frappe.get_all("Bin", fields=["warehouse"], filters={"item_code": item})
		item_warehouses = [i["warehouse"] for i in item_warehouses]
		item_list["item_warehouses"] = item_warehouses
		for wh in item_warehouses:
			root_warehouse.append(get_root_warehouse(wh))
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

	# TODO: Get dropoff node from doctype
	dropoff = [0]

	# Create the TSP solver instance.
	g = Grid_TSP(grid, scale=scale)

	# Waypoints
	unique_whs = list({item_wh["warehouse"] for item_wh in item_whs})

	# Build a mapping from warehouse to its coordinate and node.
	warehouse_to_node = {}
	for wh in unique_whs:
		loc = frappe.get_doc("Warehouse", wh).as_dict()
		coordinate = (loc["accessible_path_x"], loc["accessible_path_y"])
		warehouse_to_node[wh] = g.pos2node(coordinate)
	node_to_warehouse = {node: wh for wh, node in warehouse_to_node.items()}

	# For the TSP solver, create a list of nodes corresponding to each unique warehouse.
	pickup_list = list(warehouse_to_node.values())

	# Solve
	tsp_route, tsp_distance, pickup_order = g.tsp(dropoff, pickup_list)

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
	itemdict = {}
	for loc in doc["locations"]:
		if itemdict.get(loc["item_code"]):
			itemdict[loc["item_code"]]["qty"] += loc["qty"]
		else:
			itemdict[loc["item_code"]] = {"qty": loc["qty"]}
	company = doc["company"]
	root_warehouses = [get_root_warehouse(loc["warehouse"]) for loc in doc["locations"]]

	# Ensure all locations share the same root warehouse
	if not all(wh == root_warehouses[0] for wh in root_warehouses):
		frappe.ValidationError("All items in pick list do not share a common warehouse plan")
		return

	root_warehouse = root_warehouses[0]

	item_whs = []
	for item in itemdict.keys():
		if strategy == "FIFO":
			item_whs += Rules.FIFO(item, itemdict[item]["qty"], company, root_warehouse=root_warehouse)
		elif strategy == "LIFO":
			item_whs += Rules.LIFO(item, itemdict[item]["qty"], company, root_warehouse=root_warehouse)
		elif strategy == "Deplete maximum number of Bins":
			item_whs += Rules.deplete_max_bins(
				item, itemdict[item]["qty"], company, root_warehouse=root_warehouse
			)
		elif strategy == "Deplete minimum number of Bins":
			item_whs += Rules.deplete_min_bins(
				item, itemdict[item]["qty"], company, root_warehouse=root_warehouse
			)

	return optimize_route_picklist(item_whs, root_warehouse)
