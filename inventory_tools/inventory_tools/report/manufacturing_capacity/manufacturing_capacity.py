# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Sum
from pypika.terms import ExistsCriterion


def execute(filters=None):
	data = get_data(filters)
	return get_columns(filters), data


def get_columns(filters=None):
	return [
		{
			"label": frappe._("BOM"),
			"fieldname": "bom",
			"fieldtype": "Link",
			"options": "BOM",
			"width": 200,
		},
		{
			"label": frappe._("Item"),
			"fieldname": "item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 120,
		},
		{
			"label": frappe._("Description"),
			"fieldname": "description",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": frappe._("Qty Per Parent BOM"),
			"fieldname": "qty_per_parent_bom",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": frappe._("BOM UoM"),
			"fieldname": "bom_uom",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": frappe._("Demanded Qty"),
			"fieldname": "demanded_qty",
			"fieldtype": "Float",
			"width": 110,
		},
		{
			"label": frappe._("In Stock Qty"),
			"fieldname": "in_stock_qty",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": frappe._("Parts Can Build"),
			"fieldname": "parts_can_build_qty",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"label": frappe._("Difference Qty"),
			"fieldname": "difference_qty",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"label": frappe._("Is Selected BOM"),
			"fieldname": "is_selected_bom",
			"fieldtype": "Int",
			"width": 10,
			"hidden": 1,
		},
	]


def get_data(filters=None):
	parent_set = set()
	get_bom_parents(filters.get("bom"), parent_set)
	bom_data = []

	for idx, bom_no in enumerate(parent_set, 1):
		filters["root_parent_index"] = idx
		demanded_qty = get_total_demand(bom_no)
		indent = 0

		# Append the root parent-level BOM data
		parent_data = get_bom_data(bom_no, demanded_qty, filters, indent, is_root=True)[0]
		bom_data.append(parent_data)
		parent_index = len(bom_data) - 1

		# Append sub-level BOM data
		get_child_bom_data(bom_no, bom_data, demanded_qty, filters, indent=indent + 1, is_root=False)

		# Find the parts_can_build_qty for BOM levels - calculated as min of that BOM's children's parts_can_build_qty
		bom_data[parent_index]["parts_can_build_qty"] = set_min_can_build(
			idx, indent + 1, parent_data.bom, bom_data
		)

	# Recalculate the difference quantity for all rows
	# - BOM rows: in_stock_qty + parts_can_build_qty - demanded_qty (parts can build based off sub-assembly availability, NOT what's already in stock, so need to include that separately)
	# - Raw materials rows: parts_can_build_qty - demanded_qty (parts can build based off what's in stock, so already accounted for)
	for row in bom_data:
		if row.bom:
			row.difference_qty = row.in_stock_qty + row.parts_can_build_qty - row.demanded_qty
		else:
			row.difference_qty = row.parts_can_build_qty - row.demanded_qty

	return bom_data


def get_bom_parents(bom_no, parent_set):
	"""
	Given the name of a BOM and a set, recursively looks for the top-level parent BOM and collects
	them in parent_set

	:param bom_name: str, name of a BOM
	:param parent_set: set
	:return: None; set is manipulated in place
	"""
	item = frappe.get_value("BOM", bom_no, "item")
	parents = frappe.get_all("BOM Item", {"item_name": item}, "parent")
	if not parents:
		parent_set.add(bom_no)
	else:
		for p in parents:
			get_bom_parents(p["parent"], parent_set)


def get_total_demand(bom_no):
	"""
	For a given BOM, collects the manufacturing demand for the BOM item across outstanding Sales
	Orders, Material Requests of type "Manufacture", and Work Orders. For SOs and MRs, nets out
	the ordered quantity (accounted for in Work Orders created off them) and for WOs, nets out
	any produced quantity.

	:param bom_no: str; BOM name for whose item to find demand for
	:return: int | float
	"""
	item = frappe.get_value("BOM", bom_no, "item")

	so = frappe.qb.DocType("Sales Order")
	so_item = frappe.qb.DocType("Sales Order Item")
	so_status_criteria = [so.status == s for s in ("To Deliver and Bill", "To Deliver")]

	so_query = (
		frappe.qb.from_(so)
		.inner_join(so_item)
		.on(so_item.parent == so.name)
		.select(
			(Sum(so_item.stock_qty - so_item.work_order_qty)).as_(
				"total"
			)  # removes anything accounted for on a Work Order
		)
		.where(so.docstatus == 1)
		.where(Criterion.any(so_status_criteria))
		.where(so_item.item_code == item)
		.groupby(so_item.item_code)
	).run(as_dict=True)

	mr = frappe.qb.DocType("Material Request")
	mr_item = frappe.qb.DocType("Material Request Item")

	mr_query = (
		frappe.qb.from_(mr)
		.inner_join(mr_item)
		.on(mr_item.parent == mr.name)
		.select(
			(Sum(mr_item.stock_qty - mr_item.ordered_qty)).as_(
				"total"
			)  # removes ordered-qty, labeled as "Completed Qty" (accounted for in a Work Order)
		)
		.where(mr.docstatus == 1)
		.where(mr.status != "Stopped")
		.where(mr.material_request_type == "Manufacture")
		.where(mr_item.item_code == item)
		.groupby(mr_item.item_code)
	).run(as_dict=True)

	wo = frappe.qb.DocType("Work Order")
	wo_status_criteria = [wo.status == s for s in ("Submitted", "Not Started", "In Process")]

	wo_query = (
		frappe.qb.from_(wo)
		.select((Sum(wo.qty - wo.produced_qty)).as_("total"))
		.where(wo.docstatus == 1)
		.where(wo.production_item == item)
		.where(Criterion.any(wo_status_criteria))
		.groupby(wo.production_item)
	).run(as_dict=True)

	all_totals = so_query + mr_query + wo_query
	return sum(d["total"] for d in all_totals)


def get_bom_data(bom_no, demanded_qty, filters, indent, is_root=False):
	"""
	Collects column data for either parent BOM (top-level) if is_root is True, or the BOM Item
	data for all of the given BOM's children

	:param bom_no: str; BOM name to collect data for
	:demanded_qty: int | float; the total demand for given BOM's item
	:filters: dict; contains the data (BOM and Warehouse) passed on by user
	:indent: int; current level in BOM hierarchy
	:is_root: bool; True if the given bom_no is the top-level parent in a hierarchy,
	False if not
	"""
	warehouse_details = frappe.db.get_value(
		"Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1
	)

	BOM = frappe.qb.DocType("BOM")
	ITEM = frappe.qb.DocType("Item")
	BOM_ITEM = frappe.qb.DocType("BOM Item")
	BIN = frappe.qb.DocType("Bin")
	WH = frappe.qb.DocType("Warehouse")
	CONDITIONS = ()

	if warehouse_details:
		CONDITIONS = ExistsCriterion(
			frappe.qb.from_(WH)
			.select(WH.name)
			.where(
				(WH.lft >= warehouse_details.lft)
				& (WH.rgt <= warehouse_details.rgt)
				& (BIN.warehouse == WH.name)
			)
		)
	else:
		CONDITIONS = BIN.warehouse == filters.get("warehouse")

	if is_root:
		query = (
			frappe.qb.from_(BOM)
			.inner_join(ITEM)
			.on(BOM.item == ITEM.item_code)
			.left_join(BIN)
			.on((ITEM.item_code == BIN.item_code) & (CONDITIONS))
			.select(
				(BOM.name).as_("bom"),
				(BOM.item).as_("item"),
				ITEM.description,
				(BOM.quantity).as_("qty_per_parent_bom"),
				(ITEM.stock_uom).as_("bom_uom"),
				(BOM.quantity * demanded_qty / BOM.quantity).as_(
					"demanded_qty"
				),  # redundant calc but needs cols and avoid errors
				Sum(BIN.actual_qty).as_("in_stock_qty"),
				Sum(BIN.actual_qty).as_("orig_parts_can_build_qty"),
			)
			.where(BOM.name == bom_no)
			.groupby(BOM.item)
		)
	else:
		query = (
			frappe.qb.from_(BOM)
			.inner_join(BOM_ITEM)
			.on(BOM.name == BOM_ITEM.parent)
			.left_join(BIN)
			.on((BOM_ITEM.item_code == BIN.item_code) & (CONDITIONS))
			.select(
				(BOM_ITEM.bom_no).as_("bom"),
				(BOM_ITEM.item_code).as_("item"),
				BOM_ITEM.description,
				(BOM_ITEM.stock_qty).as_("qty_per_parent_bom"),
				(BOM_ITEM.stock_uom).as_("bom_uom"),
				(BOM_ITEM.stock_qty * demanded_qty / BOM.quantity).as_("demanded_qty"),
				Sum(BIN.actual_qty).as_("in_stock_qty"),
				Sum(BIN.actual_qty / (BOM_ITEM.stock_qty / BOM.quantity)).as_("orig_parts_can_build_qty"),
			)
			.where((BOM_ITEM.parent == bom_no) & (BOM_ITEM.parenttype == "BOM"))
			.groupby(BOM_ITEM.item_code)
		)

	results = query.run(as_dict=True)
	for r in results:
		r.update(
			{
				"in_stock_qty": r.in_stock_qty or 0,
				"orig_parts_can_build_qty": int(r.orig_parts_can_build_qty)
				if r.orig_parts_can_build_qty
				else 0,
				"is_selected_bom": int(r.bom == filters.get("bom")),
				"parent_bom": "" if is_root else bom_no,
				"root_parent_index": filters.get("root_parent_index") or 0,
				"indent": indent,
			}
		)

	return results


def get_child_bom_data(bom_no, bom_data, demanded_qty, filters, indent=0, is_root=False):
	"""
	Recursively collects BOM tree data for a given 'parent' BOM, mutates bom_data in place

	:param bom_no: str; parent BOM name
	:param bom_data: list
	:param demanded_qty: int | float; the demanded quantity (to produce) of parent BOM
	:filters: dict; holds report inputs
	:indent: int; tracks the BOM levels
	:is_root: bool; whether or not the current bom_no is the root parent BOM
	    :return: None; appends children to bom_data list in place
	"""
	children_data = get_bom_data(bom_no, demanded_qty, filters, indent=indent, is_root=is_root)
	for child in children_data:
		bom_data.append(child)
		if child.bom:
			demanded_qty = child.demanded_qty
			get_child_bom_data(child.bom, bom_data, demanded_qty, filters, indent=indent + 1)


def set_min_can_build(root_parent_index, indent, parent_bom, bom_data):
	"""
	Recursively finds and sets the parts_can_build_qty by finding the direct children of the current
	    level in the hierarchy, and taking the minimum of their parts_can_build_qty
	"""
	sub_bom_list = [
		item
		for item in bom_data
		if item.root_parent_index == root_parent_index
		and item.indent == indent
		and item.parent_bom == parent_bom
	]
	for item in sub_bom_list:
		if not item.bom:
			item["parts_can_build_qty"] = item.orig_parts_can_build_qty
		else:
			item["parts_can_build_qty"] = set_min_can_build(
				item.root_parent_index, item.indent + 1, item.bom, bom_data
			)
	return min(item.parts_can_build_qty for item in sub_bom_list)
