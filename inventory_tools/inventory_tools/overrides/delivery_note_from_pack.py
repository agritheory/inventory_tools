# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""Map Delivery Notes from Packing Slip or Shipment with Sales Order context."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.mapper import map_child_doc
from frappe.utils import flt

from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from erpnext.stock.doctype.pick_list.pick_list import (
	set_delivery_note_missing_values,
	update_delivery_note_item,
)

from inventory_tools.inventory_tools.overrides.delivery_note import apply_customer_delivery_address
from inventory_tools.inventory_tools.overrides.alternative_sales_workflow import (
	ensure_alternative_sales_workflow_enabled,
)


DELIVERY_NOTE_ITEM_MAPPER = {
	"doctype": "Delivery Note Item",
	"field_map": {
		"rate": "rate",
		"name": "so_detail",
		"parent": "against_sales_order",
	},
}


def get_single_sales_order_from_lines(rows) -> str:
	sales_orders = {row.get("against_sales_order") for row in rows if row.get("against_sales_order")}
	if not sales_orders:
		frappe.throw(_("No linked Sales Order was found on this document"))
	if len(sales_orders) > 1:
		frappe.throw(_("Alternative Sales Workflow supports one Sales Order per document"))
	return next(iter(sales_orders))


def resolve_so_detail(row) -> str | None:
	so_detail = row.get("so_detail")
	if so_detail:
		return so_detail
	dn_detail = row.get("dn_detail")
	if dn_detail:
		return frappe.db.get_value("Delivery Note Item", dn_detail, "so_detail")
	return None


def get_warehouse_for_pack_line(row, so_item) -> str | None:
	dn_detail = row.get("dn_detail")
	if dn_detail:
		warehouse = frappe.db.get_value("Delivery Note Item", dn_detail, "warehouse")
		if warehouse:
			return warehouse
	return so_item.warehouse


def get_line_qty(row, so_item) -> float:
	if row.get("qty"):
		return flt(row.qty)
	return flt(so_item.qty) - flt(so_item.delivered_qty)


def map_sales_order_items_to_delivery_note(dn, lines) -> None:
	dn.items = []

	for idx, row in enumerate(lines, start=1):
		so_detail = resolve_so_detail(row)
		if not so_detail:
			frappe.throw(_("Row {0} has no Sales Order Item reference").format(idx))

		so_item = frappe.get_doc("Sales Order Item", so_detail)
		dn_item = map_child_doc(so_item, dn, DELIVERY_NOTE_ITEM_MAPPER)
		if not dn_item:
			continue

		dn_item.qty = get_line_qty(row, so_item)
		dn_item.warehouse = get_warehouse_for_pack_line(row, so_item)
		update_delivery_note_item(so_item, dn_item, dn)


def get_draft_delivery_note_target(delivery_note_name: str | None):
	if not delivery_note_name:
		return None
	if frappe.db.get_value("Delivery Note", delivery_note_name, "docstatus") != 0:
		return None
	return frappe.get_doc("Delivery Note", delivery_note_name)


def make_delivery_note_from_packing_slip(packing_slip_name: str, target_doc=None):
	ps = frappe.get_doc("Packing Slip", packing_slip_name)
	so_name = get_single_sales_order_from_lines(ps.items)
	company = frappe.db.get_value("Sales Order", so_name, "company")
	ensure_alternative_sales_workflow_enabled(company)

	if target_doc is None:
		target_doc = get_draft_delivery_note_target(ps.delivery_note)

	dn = make_delivery_note(so_name, target_doc, kwargs={"skip_item_mapping": True})
	if not dn:
		frappe.throw(_("Could not create Delivery Note from Sales Order {0}").format(so_name))

	map_sales_order_items_to_delivery_note(dn, ps.items)
	apply_customer_delivery_address(dn)
	set_delivery_note_missing_values(dn)
	dn.save()
	link_packing_slip_to_delivery_note(ps, dn)
	return dn


def link_packing_slip_to_delivery_note(packing_slip, delivery_note) -> None:
	if packing_slip.delivery_note != delivery_note.name:
		packing_slip.db_set("delivery_note", delivery_note.name)

	dn_items_by_so_detail = {row.so_detail: row.name for row in delivery_note.items if row.so_detail}
	for item in packing_slip.items:
		dn_detail = dn_items_by_so_detail.get(item.so_detail or resolve_so_detail(item))
		if dn_detail and item.dn_detail != dn_detail:
			frappe.db.set_value("Packing Slip Item", item.name, "dn_detail", dn_detail)


def make_delivery_note_from_shipment(shipment_name: str, target_doc=None):
	shipment = frappe.get_doc("Shipment", shipment_name)
	rows = shipment.get("shipment_delivery_note") or []
	if not rows:
		frappe.throw(_("Shipment has no delivery lines"))

	so_name = get_single_sales_order_from_lines(rows)
	company = shipment.pickup_company or frappe.db.get_value("Sales Order", so_name, "company")
	ensure_alternative_sales_workflow_enabled(company)

	if target_doc is None:
		target_doc = get_draft_delivery_note_target(shipment.get("delivery_note"))
	if target_doc is None:
		for row in rows:
			target_doc = get_draft_delivery_note_target(row.delivery_note)
			if target_doc:
				break

	dn = make_delivery_note(so_name, target_doc, kwargs={"skip_item_mapping": True})
	if not dn:
		frappe.throw(_("Could not create Delivery Note from Sales Order {0}").format(so_name))

	map_sales_order_items_to_delivery_note(dn, rows)
	apply_customer_delivery_address(dn)
	set_delivery_note_missing_values(dn)
	dn.save()
	link_shipment_to_delivery_note(shipment, dn)
	return dn


def link_shipment_to_delivery_note(shipment, delivery_note) -> None:
	dn_items_by_so_detail = {row.so_detail: row for row in delivery_note.items if row.so_detail}
	changed = False

	if shipment.meta.has_field("delivery_note") and shipment.delivery_note != delivery_note.name:
		shipment.delivery_note = delivery_note.name
		changed = True

	for row in shipment.shipment_delivery_note:
		so_detail = row.so_detail or resolve_so_detail(row)
		dn_item = dn_items_by_so_detail.get(so_detail)
		if not dn_item:
			continue
		if row.delivery_note != delivery_note.name:
			row.delivery_note = delivery_note.name
			changed = True
		if (
			frappe.get_meta("Shipment Delivery Note").has_field("dn_detail")
			and row.dn_detail != dn_item.name
		):
			row.dn_detail = dn_item.name
			changed = True

	if changed:
		shipment.save()
