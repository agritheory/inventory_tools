# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""Propagate Sales Order identity (against_sales_order + so_detail) on workflow child rows."""

from __future__ import annotations

import frappe


def has_so_identity_fields(doctype: str) -> bool:
	meta = frappe.get_meta(doctype)
	return meta.has_field("against_sales_order") and meta.has_field("so_detail")


def get_delivery_note_item_so_identity(dn_detail: str | None) -> dict | None:
	if not dn_detail:
		return None
	return frappe.db.get_value(
		"Delivery Note Item",
		dn_detail,
		["against_sales_order", "so_detail"],
		as_dict=True,
	)


def apply_so_identity(row, against_sales_order: str | None, so_detail: str | None) -> None:
	if not against_sales_order or not so_detail:
		return
	if row.get("so_detail"):
		return
	row.against_sales_order = against_sales_order
	row.so_detail = so_detail


def stamp_packing_slip_items_from_delivery_note(packing_slip) -> None:
	if not has_so_identity_fields("Packing Slip Item"):
		return

	for item in packing_slip.get("items") or []:
		if item.get("so_detail"):
			continue
		so_identity = get_delivery_note_item_so_identity(item.get("dn_detail"))
		if so_identity:
			apply_so_identity(item, so_identity.against_sales_order, so_identity.so_detail)


def stamp_shipment_delivery_notes_from_delivery_note(shipment) -> None:
	if not has_so_identity_fields("Shipment Delivery Note"):
		return

	for row in shipment.get("shipment_delivery_note") or []:
		if row.get("so_detail"):
			continue

		dn_detail = row.get("dn_detail")
		if dn_detail:
			so_identity = get_delivery_note_item_so_identity(dn_detail)
			if so_identity:
				apply_so_identity(row, so_identity.against_sales_order, so_identity.so_detail)
				continue

		delivery_note = row.get("delivery_note")
		if not delivery_note:
			continue

		dn_items = frappe.get_all(
			"Delivery Note Item",
			filters={"parent": delivery_note},
			fields=["against_sales_order", "so_detail"],
			limit=1,
		)
		if dn_items:
			apply_so_identity(row, dn_items[0].against_sales_order, dn_items[0].so_detail)


def stamp_stock_entry_items_from_pick_list(stock_entry) -> None:
	if not has_so_identity_fields("Stock Entry Detail"):
		return

	for row in stock_entry.get("items") or []:
		if row.get("so_detail") or not row.get("pick_list_item"):
			continue

		pick_list_item = frappe.db.get_value(
			"Pick List Item",
			row.pick_list_item,
			["sales_order", "sales_order_item"],
			as_dict=True,
		)
		if pick_list_item and pick_list_item.sales_order:
			apply_so_identity(row, pick_list_item.sales_order, pick_list_item.sales_order_item)


def stamp_packing_slip_on_validate(doc, method=None) -> None:
	stamp_packing_slip_items_from_delivery_note(doc)


def stamp_shipment_on_validate(doc, method=None) -> None:
	stamp_shipment_delivery_notes_from_delivery_note(doc)


def stamp_stock_entry_before_save(doc, method=None) -> None:
	stamp_stock_entry_items_from_pick_list(doc)
