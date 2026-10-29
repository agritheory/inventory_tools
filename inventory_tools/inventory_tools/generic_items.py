# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt


def validate_generic_item(doc, method=None):
	if cint(doc.is_generic_item) and cint(doc.is_stock_item):
		frappe.throw(_("Generic items must not be stock items."))


def generic_items_enabled(company):
	if not company or not frappe.db.exists("Inventory Tools Settings", company):
		return False
	return cint(frappe.db.get_value("Inventory Tools Settings", company, "enable_generic_items"))


def get_generic_material_request_items(mr_item_names):
	names = [name for name in mr_item_names if name]
	if not names:
		return set()

	material_request_item = frappe.qb.DocType("Material Request Item")
	item = frappe.qb.DocType("Item")
	rows = (
		frappe.qb.from_(material_request_item)
		.inner_join(item)
		.on(material_request_item.item_code == item.name)
		.select(material_request_item.name)
		.where(material_request_item.name.isin(names))
		.where(item.is_generic_item == 1)
	).run()
	return {row[0] for row in rows}


def validate_generic_purchase_order_rows(po, generic_mr_items):
	for row in po.get("items") or []:
		if row.material_request_item not in generic_mr_items:
			continue
		mr_project = frappe.db.get_value("Material Request Item", row.material_request_item, "project")
		if mr_project and row.project != mr_project:
			frappe.throw(
				_("Row {0}: Project must be equal to '{1}'").format(row.idx, mr_project),
				title=_("Incorrect Value"),
			)


def update_generic_material_request_ordered_qty(doc):
	if not generic_items_enabled(doc.company):
		return

	mr_item_names = {row.material_request_item for row in doc.get("items") or [] if row.material_request_item}
	generic_mr_items = get_generic_material_request_items(mr_item_names)
	if not generic_mr_items:
		return

	purchase_order_item = frappe.qb.DocType("Purchase Order Item")
	updated_material_requests = set()

	for mri_name in generic_mr_items:
		ordered_amount = (
			frappe.qb.from_(purchase_order_item)
			.select(Sum(purchase_order_item.base_net_amount))
			.where(purchase_order_item.material_request_item == mri_name)
			.where(purchase_order_item.docstatus == 1)
		).run()[0][0]
		ordered_amount = flt(ordered_amount)

		mr_row = frappe.db.get_value(
			"Material Request Item",
			mri_name,
			["stock_qty", "amount", "parent"],
			as_dict=True,
		)
		if not mr_row:
			continue

		stock_qty = flt(mr_row.stock_qty)
		amount = flt(mr_row.amount)
		if amount > 0:
			ordered_qty = stock_qty * ordered_amount / amount
		elif ordered_amount > 0:
			ordered_qty = stock_qty
		else:
			ordered_qty = 0

		frappe.db.set_value("Material Request Item", mri_name, "ordered_qty", ordered_qty)
		updated_material_requests.add(mr_row.parent)

	percent_args = {
		"target_dt": "Material Request Item",
		"target_parent_dt": "Material Request",
		"target_parent_field": "per_ordered",
		"target_ref_field": "stock_qty",
		"target_field": "ordered_qty",
	}
	for material_request in updated_material_requests:
		doc._update_percent_field({**percent_args, "name": material_request})


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

	is_generic = cint(frappe.db.get_value("Item", row.item_code, "is_generic_item"))
	return {
		"is_generic": bool(is_generic),
		"item_code": row.item_code,
		"material_request": row.parent,
	}
