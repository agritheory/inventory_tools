# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.doctype.pick_list.pick_list import PickList as ERPNextPickList
from frappe.utils.data import nowdate


class InventoryToolsPickList(ERPNextPickList):
	def get_default_strategy(self) -> str | None:
		if not self.company:
			return None
		return frappe.db.get_value(
			"Inventory Tools Settings",
			{"company": self.company},
			"default_route_optimization_strategy",
		)

	def after_mapping(self, source_doc):  # noqa
		strategy = self.get_default_strategy()
		self.set_onload("default_route_optimization_strategy", strategy or "Use Source Document Order")
		if not strategy or strategy == "Use Source Document Order" or not self.get("locations"):
			return
		try:
			result = optimize_path(self.as_dict(), strategy)
			self.set("locations", [])
			for item in result:
				self.append("locations", item)
		except Exception:
			pass

	def onload(self):
		strategy = self.get_default_strategy()
		self.set_onload("default_route_optimization_strategy", strategy or "Use Source Document Order")


class PathFinder:
	@staticmethod
	def process_entries(item_code, qty, company, order_by_clauses, plan_warehouses, to_date):
		SLE = frappe.qb.DocType("Stock Ledger Entry")
		query = (
			frappe.qb.from_(SLE)
			.select(SLE.actual_qty, SLE.posting_date, SLE.creation, SLE.warehouse)
			.where(SLE.item_code == item_code)
			.where(SLE.company == company)
			.where(SLE.posting_date <= to_date)
			.where(SLE.is_cancelled == 0)
			.where(SLE.actual_qty > 0)
		)
		if plan_warehouses:
			query = query.where(SLE.warehouse.isin(list(plan_warehouses)))
		for field, order in order_by_clauses:
			query = query.orderby(field, order=order)

		sle = query.run(as_dict=True)

		newsle = []
		qty_obtained = 0

		for entry in sle:
			remaining_qty = qty - qty_obtained

			if entry["actual_qty"] >= remaining_qty:
				newsle.append({"item_code": item_code, "warehouse": entry["warehouse"], "qty": remaining_qty})
				qty_obtained += remaining_qty
				break
			else:
				newsle.append(
					{"item_code": item_code, "warehouse": entry["warehouse"], "qty": entry["actual_qty"]}
				)
				qty_obtained += entry["actual_qty"]

		if (qty - qty_obtained) != 0:
			raise frappe.ValidationError("Not enough items in root warehouse")
		return newsle

	@staticmethod
	def FIFO(item_code, qty, company, plan_warehouses=None, to_date=None):
		SLE = frappe.qb.DocType("Stock Ledger Entry")
		order_by = [(SLE.posting_date, frappe.qb.asc), (SLE.creation, frappe.qb.asc)]
		return PathFinder.process_entries(
			item_code, qty, company, order_by, plan_warehouses, to_date or nowdate()
		)

	@staticmethod
	def LIFO(item_code, qty, company, plan_warehouses=None, to_date=None):
		SLE = frappe.qb.DocType("Stock Ledger Entry")
		order_by = [(SLE.posting_date, frappe.qb.desc), (SLE.creation, frappe.qb.desc)]
		return PathFinder.process_entries(
			item_code, qty, company, order_by, plan_warehouses, to_date or nowdate()
		)

	@staticmethod
	def deplete_max_bins(item_code, qty, company, plan_warehouses=None, to_date=None):
		SLE = frappe.qb.DocType("Stock Ledger Entry")
		order_by = [
			(SLE.actual_qty, frappe.qb.asc),
			(SLE.posting_date, frappe.qb.asc),
			(SLE.creation, frappe.qb.asc),
		]
		return PathFinder.process_entries(
			item_code, qty, company, order_by, plan_warehouses, to_date or nowdate()
		)

	@staticmethod
	def deplete_min_bins(item_code, qty, company, plan_warehouses=None, to_date=None):
		SLE = frappe.qb.DocType("Stock Ledger Entry")
		order_by = [
			(SLE.actual_qty, frappe.qb.desc),
			(SLE.posting_date, frappe.qb.asc),
			(SLE.creation, frappe.qb.asc),
		]
		return PathFinder.process_entries(
			item_code, qty, company, order_by, plan_warehouses, to_date or nowdate()
		)


def get_root_warehouse(warehouse):
	WP = frappe.qb.DocType("Warehouse Plan")
	has_matrix = (
		frappe.qb.from_(WP).select(WP.name).where((WP.name == warehouse) & (WP.matrix.isnotnull())).run()
	)
	if has_matrix:
		return warehouse

	Wh = frappe.qb.DocType("Warehouse")
	result = frappe.qb.from_(Wh).select(Wh.warehouse_plan).where(Wh.name == warehouse).run()
	if result and result[0][0]:
		return result[0][0]
	raise frappe.ValidationError(f"Warehouse '{warehouse}' is not part of any Warehouse Plan")


@frappe.whitelist()
def optimize_route_picklist(item_whs: list, root_warehouse: str) -> list:
	"""Optimize the pick-up route for a list of items.

	This function takes a list of dictionaries, each representing an item along with its warehouse
	location, and returns the list reordered based on an optimized pick-up sequence.

	Expected format of `item_whs`:
	        [
	                {
	                        'item_code': <str>,  # The code identifying the item.
	                        'warehouse': <str>  # The warehouse where the item is located.
	                },
	                ...
	        ]

	Returns:
	        list: A reordered list of dictionaries, optimized for the pick-up route.
	"""
	wp = frappe.get_cached_doc("Warehouse Plan", root_warehouse)
	g = wp.graph
	dropoff = [g.pos2node((wp.pickup_point_x, wp.pickup_point_y))]

	unique_whs = list({item_wh["warehouse"] for item_wh in item_whs})

	Wh = frappe.qb.DocType("Warehouse")
	wh_paths = (
		frappe.qb.from_(Wh)
		.select(Wh.name, Wh.accessible_path)
		.where(Wh.name.isin(unique_whs))
		.run(as_dict=True)
	)
	warehouse_to_node = {
		row.name: g.pos2node(tuple(int(x) for x in row.accessible_path.split(","))) for row in wh_paths
	}
	node_to_warehouse = {node: wh for wh, node in warehouse_to_node.items()}

	pickup_list = list(warehouse_to_node.values())
	pickup_order, *rest = g.tsp(dropoff, pickup_list)
	warehouse_order_map = {}
	for order_index, node in enumerate(pickup_order):
		wh = node_to_warehouse[node]
		warehouse_order_map[wh] = order_index

	sorted_item_whs = sorted(
		item_whs,
		key=lambda item: (warehouse_order_map[item["warehouse"]], item["item_code"], item["qty"]),
	)
	return sorted_item_whs


@frappe.whitelist()
def optimize_path(doc: str | dict, strategy: str) -> list[dict]:
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
		doc_dict: dict = frappe.get_doc("Pick List", doc).as_dict()
	else:
		doc_dict = doc

	itemdict: dict[str, dict[str, float]] = {}
	for loc in doc_dict["locations"]:
		code = loc["item_code"]
		qty = loc["qty"]
		if code in itemdict:
			itemdict[code]["qty"] += qty
		else:
			itemdict[code] = {"qty": qty}

	company = doc_dict["company"]

	unique_locations = {loc["warehouse"] for loc in doc_dict["locations"]}
	root_wh_map = {wh: get_root_warehouse(wh) for wh in unique_locations}
	root_warehouses = [root_wh_map[loc["warehouse"]] for loc in doc_dict["locations"]]

	if not all(wh == root_warehouses[0] for wh in root_warehouses):
		raise frappe.ValidationError("All items in pick list do not share a common warehouse plan")

	root_warehouse = root_warehouses[0]

	Wh = frappe.qb.DocType("Warehouse")
	plan_warehouses = frozenset(
		frappe.qb.from_(Wh).select(Wh.name).where(Wh.warehouse_plan == root_warehouse).run(pluck=True)
	)

	item_whs = []
	for item in itemdict.keys():
		if strategy == "FIFO":
			item_whs += PathFinder.FIFO(
				item, itemdict[item]["qty"], company, plan_warehouses=plan_warehouses
			)
		elif strategy == "LIFO":
			item_whs += PathFinder.LIFO(
				item, itemdict[item]["qty"], company, plan_warehouses=plan_warehouses
			)
		elif strategy == "Deplete maximum number of Bins":
			item_whs += PathFinder.deplete_max_bins(
				item, itemdict[item]["qty"], company, plan_warehouses=plan_warehouses
			)
		elif strategy == "Deplete minimum number of Bins":
			item_whs += PathFinder.deplete_min_bins(
				item, itemdict[item]["qty"], company, plan_warehouses=plan_warehouses
			)
	try:
		return optimize_route_picklist(item_whs, root_warehouse)
	except Exception as e:
		raise e
