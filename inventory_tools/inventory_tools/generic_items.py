# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt


def validate_generic_item(doc, method=None):
	if cint(doc.is_generic_item) and cint(doc.is_stock_item):
		frappe.throw(_("Generic items must not be stock items."))


def get_generic_item_rows(doc):
	tables = {"Pick List": ("locations",), "Subcontracting Order": ("items", "service_items")}.get(
		doc.doctype, ("items",)
	)
	rows = [row for table in tables for row in doc.get(table) or [] if row.get("item_code")]
	if not rows or not frappe.get_meta("Item").has_field("is_generic_item"):
		return []
	generic = set(
		frappe.get_all(
			"Item",
			filters={"name": ["in", list({row.item_code for row in rows})], "is_generic_item": 1},
			pluck="name",
		)
	)
	return [row for row in rows if row.item_code in generic]


def reject_generic_items(doc, method=None):
	"""
	Generic items are placeholders on Material Requests and draft Purchase Orders only; the
	buyer must replace them with the specific Item before anything is ordered, moved or billed.
	"""
	rows = get_generic_item_rows(doc)
	if not rows:
		return
	frappe.throw(
		_(
			"Replace generic placeholder items with the specific Item before using them on a {0}: {1}"
		).format(
			_(doc.doctype),
			", ".join(_("Row {0} ({1})").format(row.idx, row.item_code) for row in rows),
		),
		title=_("Generic Item"),
	)


def validate_generic_item_price(doc, method=None):
	if doc.item_code and cint(frappe.db.get_value("Item", doc.item_code, "is_generic_item")):
		frappe.throw(_("Item Price cannot be created for generic placeholder items."))


def generic_items_enabled(company):
	if not company or not frappe.db.exists("Inventory Tools Settings", company):
		return False
	return cint(frappe.db.get_value("Inventory Tools Settings", company, "enable_generic_items"))


def get_generic_qty_mismatch_policy(company):
	return (
		frappe.db.get_value("Inventory Tools Settings", company, "generic_item_qty_mismatch") or "Warn"
	)


def get_generic_material_request_items(mr_item_names):
	"""
	Returns Material Request Items in `mr_item_names` whose item is still a generic item,
	keyed by Material Request Item name.
	"""
	names = [name for name in mr_item_names if name]
	if not names:
		return {}

	material_request_item = frappe.qb.DocType("Material Request Item")
	item = frappe.qb.DocType("Item")
	rows = (
		frappe.qb.from_(material_request_item)
		.inner_join(item)
		.on(material_request_item.item_code == item.name)
		.select(
			material_request_item.name,
			material_request_item.parent,
			material_request_item.item_code,
			material_request_item.qty,
			material_request_item.uom,
			material_request_item.project,
		)
		.where(material_request_item.name.isin(names))
		.where(item.is_generic_item == 1)
	).run(as_dict=True)
	return {row.name: row for row in rows}


def get_replaced_generic_rows(po, generic_mr_items):
	"""
	Purchase Order rows linked to a generic Material Request Item where the buyer has
	selected a different item.
	"""
	return [
		row
		for row in po.get("items") or []
		if row.material_request_item in generic_mr_items
		and row.item_code != generic_mr_items[row.material_request_item].item_code
	]


def validate_generic_purchase_order_rows(po, generic_mr_items):
	replaced_rows = get_replaced_generic_rows(po, generic_mr_items)
	if not replaced_rows:
		return

	references = [row.material_request_item for row in po.get("items") or []]
	policy = get_generic_qty_mismatch_policy(po.company)

	for row in replaced_rows:
		mr_row = generic_mr_items[row.material_request_item]

		if references.count(row.material_request_item) > 1:
			frappe.throw(
				_("Row {0}: generic item {1} from {2} can only be replaced by one Purchase Order line").format(
					row.idx, frappe.bold(mr_row.item_code), mr_row.parent
				),
				title=_("Duplicate Generic Item Replacement"),
			)

		if mr_row.project and row.project != mr_row.project:
			frappe.throw(
				_("Row {0}: Project must be equal to '{1}'").format(row.idx, mr_row.project),
				title=_("Incorrect Value"),
			)

		if policy == "Ignore" or flt(row.qty) == flt(mr_row.qty):
			continue

		message = _(
			"Row {0}: quantity {1} {2} for {3} differs from the {4} {5} requested for generic item {6} on {7}"
		).format(
			row.idx,
			flt(row.qty),
			row.uom,
			frappe.bold(row.item_code),
			flt(mr_row.qty),
			mr_row.uom,
			frappe.bold(mr_row.item_code),
			mr_row.parent,
		)
		if policy == "Error":
			frappe.throw(message, title=_("Generic Item Quantity Mismatch"))
		frappe.msgprint(message, title=_("Generic Item Quantity Mismatch"), indicator="orange")


def resolve_generic_material_request_items(po):
	"""
	Rewrites each generic Material Request Item replaced on `po` to the purchased item, keeping
	the placeholder in `generic_item_code`. Runs before ERPNext updates ordered quantities so
	the Material Request is tracked against the purchased item.
	"""
	if not generic_items_enabled(po.company):
		return

	mr_item_names = {row.material_request_item for row in po.get("items") or []}
	generic_mr_items = get_generic_material_request_items(mr_item_names)

	for row in get_replaced_generic_rows(po, generic_mr_items):
		frappe.db.set_value(
			"Material Request Item",
			row.material_request_item,
			{
				"generic_item_code": generic_mr_items[row.material_request_item].item_code,
				"item_code": row.item_code,
				"item_name": row.item_name,
				"item_group": row.item_group,
				"brand": row.brand,
				"uom": row.uom,
				"stock_uom": row.stock_uom,
				"conversion_factor": row.conversion_factor,
				"qty": row.qty,
				"stock_qty": row.stock_qty,
				"rate": row.base_rate,
				"amount": row.base_amount,
			},
		)


@frappe.whitelist()
def get_material_request_item_generic_info(material_request_item):
	if not material_request_item:
		return {}

	row = frappe.db.get_value(
		"Material Request Item",
		material_request_item,
		["item_code", "parent"],
		as_dict=True,
	)
	if not row:
		return {}

	frappe.has_permission("Material Request", "read", doc=row.parent, throw=True)
	is_generic = cint(frappe.db.get_value("Item", row.item_code, "is_generic_item"))
	return {
		"is_generic": bool(is_generic),
		"item_code": row.item_code,
		"material_request": row.parent,
	}
