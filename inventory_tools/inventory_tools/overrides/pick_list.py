from typing import TYPE_CHECKING

import frappe
from frappe.utils import safe_json_loads

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
		item_list = {}
		item_list["item"] = item
		root_warehouse = []
		item_warehouses = frappe.get_all("Bin", fields=["warehouse"], filters={"item_code": item})
		item_warehouses = [i["warehouse"] for i in item_warehouses]
		item_list["item_warehouses"] = item_warehouses
		for wh in item_warehouses:
			root_warehouse.append(get_root_warehouse(wh))

		item_list["root_warehouse"] = root_warehouse
		item_wh_list.append(item_list)
	return item_wh_list


def get_node(doc, method):
	# Get root warehouse for all items in doc
	items = [item["item_code"] for item in doc["locations"]]
	root_warehouses = [get_root_warehouse(w["warehouse"]) for w in doc["locations"]]
	all_same = all(wh == root_warehouses[0] for wh in root_warehouses)
	if all_same is True:
		root_warehouse = root_warehouses[0]

	# Get all item locations for items in doctype
	# Filter by root warehouse
	item_wh_list = list(
		filter(lambda d: d["root_warehouse"] == root_warehouse, get_all_warehouses(items))
	)

	if method == "FIFO":
		pass
	elif method == "LIFO":
		pass
	elif method == "Deplete maximum number of Bins":
		pass
	elif method == "Deplete minimum number of Bins":
		pass
	elif method == "Shortest Path":
		pass
	return 1


@frappe.whitelist()
def optimize_route_picklist(items, method):
	# grid, waypoints, pickup_node = get_all_warehouses(items)
	# nodes = []
	# item_nodes = {}
	# for item in items:
	# 	node = get_node(item, method)
	# 	nodes.append(node)
	# 	item_nodes[item] = node

	# g = Grid(grid, waypoints)
	# tsp_route, tsp_distance, pickup_order = g.tsp(pickup_node, nodes)

	# # order item list using item_nodes
	return 1
