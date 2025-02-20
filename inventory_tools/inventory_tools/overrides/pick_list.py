from typing import TYPE_CHECKING

import frappe
from frappe.utils import safe_json_loads
from inventory_tools.inventory_tools.doctype.warehouse_plan.warehouse_plan import Grid

if TYPE_CHECKING:
	from erpnext.stock.doctype.pick_list_item.pick_list_item import PickListItem
	from erpnext.stock.doctype.pick_list.pick_list import PickList


@frappe.whitelist()
def optimize_path(doc: "PickList", strategy: str) -> list["PickListItem"]:
	doc = safe_json_loads(doc) if isinstance(doc, str) else doc
	return doc.locations
	# returns a list of Pick List Item in the correct order


def validate_warehouse_has_plan(items):
	warehouses = []
	for item in items:
		warehouses.append(item["source_warehouse"])

	# get master warehouse
	master_warehose_grid = [1]
	waypoints = [1]
	pickup_node = [0]
	return master_warehose_grid, waypoints, pickup_node


def get_node(item, method):
	if method == "fifo":
		pass
	elif method == "lifo":
		pass
	elif method == "deplete_max_bins":
		pass
	elif method == "deplete_min_bins":
		pass
	return 1


@frappe.whitelist()
def optimize_route_sales_order(doc, method=None):
	pass


@frappe.whitelist()
def optimize_route_work_order(doc, method):
	items = doc.required_items

	grid, waypoints, pickup_node = validate_warehouse_has_plan(items)
	nodes = []
	item_nodes = {}
	for item in items:
		node = get_node(item, method)
		nodes.append(node)
		item_nodes[item] = node

	g = Grid(grid, waypoints)
	tsp_route, tsp_distance, pickup_order = g.tsp(pickup_node, nodes)

	# order item list using item_nodes
	return 1
