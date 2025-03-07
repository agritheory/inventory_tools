from typing import TYPE_CHECKING

import frappe
from frappe.utils import safe_json_loads
from frappe.utils.data import nowdate

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

		item_list["root_warehouse"] = root_warehouse
		item_wh_list.append(item_list)
	return item_wh_list


def optimize_picklist(doc, method):
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

	new_items = []
	for item in itemdict.keys():
		if method == "FIFO":
			new_items.append(
				Rules.FIFO(item, itemdict[item]["qty"], company, root_warehouse=root_warehouse)
			)
		elif method == "LIFO":
			new_items.append(
				Rules.LIFO(item, itemdict[item]["qty"], company, root_warehouse=root_warehouse)
			)
		elif method == "Deplete maximum number of Bins":
			new_items.append(
				Rules.deplete_max_bins(item, itemdict[item]["qty"], company, root_warehouse=root_warehouse)
			)
		elif method == "Deplete minimum number of Bins":
			new_items.append(
				Rules.deplete_max_bins(item, itemdict[item]["qty"], company, root_warehouse=root_warehouse)
			)
		elif method == "Shortest Path":
			# TODO: Select warehouses closest to pickup point
			pass

	op_list = optimize_route_picklist(new_items)
	return op_list


@frappe.whitelist()
def optimize_route_picklist(item_wh: list):
	"""
	Optimize the pick-up route for a list of items.

	This function takes a list of dictionaries, each representing an item along with its warehouse
	location, and returns the list reordered based on an optimized pick-up sequence.

	Expected format of `item_wh`:
	        [
	                {
	                        'item_code': <str>,   # The code identifying the item.
	                        'warehouse': <str>    # The warehouse where the item is located.
	                },
	                ...
	        ]

	Returns:
	        list: A reordered list of dictionaries, optimized for the pick-up route."
	"""
	return 1
