from typing import TYPE_CHECKING

import frappe
from frappe.utils import safe_json_loads

if TYPE_CHECKING:
	from erpnext.stock.doctype.pick_list_item.pick_list_item import PickListItem
	from erpnext.stock.doctype.pick_list.pick_list import PickList
	from frappe.utils.data import nowdate


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
	# Extract item codes and root warehouses from document locations
	items = [loc["item_code"] for loc in doc["locations"]]
	root_warehouses = [get_root_warehouse(loc["warehouse"]) for loc in doc["locations"]]

	# Ensure all locations share the same root warehouse
	if not all(wh == root_warehouses[0] for wh in root_warehouses):
		frappe.ValidationError("All items in pick list do not share a common warehouse plan")
		return

	root_warehouse = root_warehouses[0]

	# # Accumulate warehouse entries for each item, filtering by the common root warehouse
	# item_wh_list = [
	# 	entry
	# 	for item in items
	# 	for entry in get_all_warehouses(item)
	# 	if entry["root_warehouse"] == root_warehouse
	# ]

	# # Build the final list with item, warehouse, and quantity
	# item_wh_qty_list = [
	# 	{
	# 		"item_code": entry["item_code"],
	# 		"warehouse": entry["warehouse"],
	# 		"qty": get_item_qty(entry["item_code"], entry["warehouse"]),
	# 		"modified": get_bin_modified(entry["item_code"], entry["warehouse"]),
	# 	}
	# 	for entry in item_wh_list
	# ]

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
