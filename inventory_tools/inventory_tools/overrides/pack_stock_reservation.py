# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""Stock reservation from Packing Slip and Shipment in Alternative Sales Workflow."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.selling.doctype.sales_order.sales_order import get_unreserved_qty
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
	get_sre_reserved_qty_details_for_voucher,
	get_sre_reserved_warehouses_for_voucher,
)

from inventory_tools.inventory_tools.overrides.alternative_sales_workflow import (
	is_alternative_sales_workflow_enabled,
)
from inventory_tools.inventory_tools.overrides.delivery_note_from_pack import resolve_so_detail

RESERVE_MODES = ("Never", "Always", "Ask")
PACK_DOCTYPE_LINES = {
	"Packing Slip": "items",
	"Shipment": "shipment_delivery_note",
}


def is_stock_reservation_enabled() -> bool:
	return cint(frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"))


def get_pack_reserve_mode(company: str, pack_doctype: str) -> str:
	if not is_stock_reservation_enabled() or not is_alternative_sales_workflow_enabled(company):
		return "Never"

	field_name = (
		"reserve_stock_on_packing_slip"
		if pack_doctype == "Packing Slip"
		else "reserve_stock_on_shipment"
	)
	mode = frappe.db.get_value("Inventory Tools Settings", company, field_name)
	if mode not in RESERVE_MODES:
		return "Never" if pack_doctype == "Shipment" else "Always"
	return mode


def get_pack_lines(doc, pack_doctype: str):
	return doc.get(PACK_DOCTYPE_LINES[pack_doctype]) or []


def resolve_warehouse_for_pack_reservation(row, so_item) -> str | None:
	so_detail = resolve_so_detail(row)
	if so_detail:
		staging_warehouse = frappe.db.sql(
			"""
			select sed.t_warehouse
			from `tabStock Entry Detail` sed
			inner join `tabStock Entry` se on se.name = sed.parent
			where sed.so_detail = %s
				and se.docstatus = 1
				and sed.t_warehouse is not null
				and sed.t_warehouse != ''
			order by se.creation desc
			limit 1
			""",
			so_detail,
		)
		if staging_warehouse:
			return staging_warehouse[0][0]

	if row.get("against_sales_order") and so_detail:
		reserved_warehouses = get_sre_reserved_warehouses_for_voucher(
			"Sales Order", row.against_sales_order, so_detail
		)
		if reserved_warehouses:
			return reserved_warehouses[0]

	return so_item.warehouse


def get_reserved_warehouse_for_pack_line(row) -> str | None:
	so_detail = resolve_so_detail(row)
	if not row.get("against_sales_order") or not so_detail:
		return None
	reserved_warehouses = get_sre_reserved_warehouses_for_voucher(
		"Sales Order", row.against_sales_order, so_detail
	)
	return reserved_warehouses[0] if reserved_warehouses else None


def pack_line_qty(row, so_item) -> float:
	if row.get("qty"):
		return flt(row.qty)
	return flt(so_item.qty) - flt(so_item.delivered_qty)


def pack_lines_need_reservation(doc, pack_doctype: str) -> bool:
	if not get_pack_lines(doc, pack_doctype):
		return False

	seen_sales_orders: set[str] = set()
	for row in get_pack_lines(doc, pack_doctype):
		so_detail = resolve_so_detail(row)
		if not row.get("against_sales_order") or not so_detail:
			continue
		if row.against_sales_order not in seen_sales_orders:
			seen_sales_orders.add(row.against_sales_order)
		reserved_qty_details = get_sre_reserved_qty_details_for_voucher(
			"Sales Order", row.against_sales_order
		)
		so_item = frappe.get_doc("Sales Order Item", so_detail)
		line_qty = pack_line_qty(row, so_item)
		if flt(so_item.picked_qty) > 0:
			continue
		unreserved = get_unreserved_qty(so_item, reserved_qty_details)
		if min(unreserved, line_qty) > 0:
			return True
	return False


def create_stock_reservation_entries_from_pack(
	doc, pack_doctype: str, notify: bool = True
) -> None:
	if not is_stock_reservation_enabled():
		return

	so_items_details_map: dict[str, list[dict]] = {}
	for row in get_pack_lines(doc, pack_doctype):
		so_detail = resolve_so_detail(row)
		if not row.get("against_sales_order") or not so_detail:
			continue

		so_item = frappe.get_doc("Sales Order Item", so_detail)
		if flt(so_item.picked_qty) > 0:
			continue
		warehouse = resolve_warehouse_for_pack_reservation(row, so_item)
		if not warehouse:
			frappe.msgprint(
				_("Row #{0}: Warehouse is required to reserve stock for Item {1}.").format(
					row.idx, frappe.bold(so_item.item_code)
				),
				indicator="orange",
				title=_("Stock Reservation"),
			)
			continue

		reserved_qty_details = get_sre_reserved_qty_details_for_voucher(
			"Sales Order", row.against_sales_order
		)
		unreserved = get_unreserved_qty(so_item, reserved_qty_details)
		qty_to_reserve = min(unreserved, pack_line_qty(row, so_item))
		if qty_to_reserve <= 0:
			continue

		so_items_details_map.setdefault(row.against_sales_order, []).append(
			{
				"sales_order_item": so_detail,
				"item_code": so_item.item_code,
				"warehouse": warehouse,
				"qty_to_reserve": qty_to_reserve,
				"from_voucher_no": doc.name,
				"from_voucher_detail_no": row.name,
			}
		)

	if not so_items_details_map:
		return

	for so_name, items_details in so_items_details_map.items():
		so_doc = frappe.get_doc("Sales Order", so_name)
		existing_sre_names = set(
			frappe.get_all(
				"Stock Reservation Entry",
				filters={"voucher_type": "Sales Order", "voucher_no": so_name, "docstatus": 1},
				pluck="name",
			)
		)
		so_doc.create_stock_reservation_entries(items_details=items_details, notify=False)
		for item in items_details:
			new_sres = frappe.get_all(
				"Stock Reservation Entry",
				filters={
					"voucher_type": "Sales Order",
					"voucher_no": so_name,
					"voucher_detail_no": item["sales_order_item"],
					"docstatus": 1,
					"name": ["not in", list(existing_sre_names)],
				},
				pluck="name",
				order_by="creation desc",
			)
			for sre_name in new_sres:
				existing_sre_names.add(sre_name)
				if frappe.get_meta("Stock Reservation Entry").has_field("pack_from_doctype"):
					frappe.db.set_value(
						"Stock Reservation Entry",
						sre_name,
						{
							"pack_from_doctype": pack_doctype,
							"pack_from_name": doc.name,
							"pack_from_detail_no": item["from_voucher_detail_no"],
						},
					)

	if notify:
		frappe.msgprint(_("Stock Reservation Entries Created"), alert=True, indicator="green")


def cancel_stock_reservation_entries_from_pack(
	pack_doctype: str, pack_name: str, notify: bool = True
) -> None:
	if not frappe.get_meta("Stock Reservation Entry").has_field("pack_from_name"):
		return

	sre_list = frappe.get_all(
		"Stock Reservation Entry",
		filters={
			"pack_from_doctype": pack_doctype,
			"pack_from_name": pack_name,
			"docstatus": 1,
			"status": ["not in", ["Delivered", "Cancelled"]],
		},
		pluck="name",
	)
	if not sre_list:
		return

	for sre_name in sre_list:
		frappe.get_doc("Stock Reservation Entry", sre_name).cancel()

	if notify:
		frappe.msgprint(_("Stock Reservation Entries Cancelled"), alert=True, indicator="red")


def has_pack_originated_reservation(pack_doctype: str, pack_name: str) -> bool:
	if not frappe.get_meta("Stock Reservation Entry").has_field("pack_from_name"):
		return False
	return bool(
		frappe.db.exists(
			"Stock Reservation Entry",
			{
				"pack_from_doctype": pack_doctype,
				"pack_from_name": pack_name,
				"docstatus": 1,
				"status": ["not in", ["Delivered", "Cancelled"]],
			},
		)
	)


def maybe_reserve_stock_on_pack_submit(doc, pack_doctype: str) -> None:
	company = get_pack_company(doc, pack_doctype)
	if not company or not uses_pack_stock_reservation(doc, pack_doctype):
		return

	mode = get_pack_reserve_mode(company, pack_doctype)
	if mode == "Never" or not pack_lines_need_reservation(doc, pack_doctype):
		return

	if mode == "Ask" and not cint(doc.get("reserve_stock_on_submit")):
		return

	create_stock_reservation_entries_from_pack(doc, pack_doctype)


def get_pack_company(doc, pack_doctype: str) -> str | None:
	if pack_doctype == "Shipment" and doc.get("pickup_company"):
		return doc.pickup_company
	for row in get_pack_lines(doc, pack_doctype):
		if row.get("against_sales_order"):
			return frappe.db.get_value("Sales Order", row.against_sales_order, "company")
	return None


def uses_pack_stock_reservation(doc, pack_doctype: str) -> bool:
	if pack_doctype == "Packing Slip":
		if doc.get("delivery_note"):
			return False
		return any(row.get("so_detail") for row in get_pack_lines(doc, pack_doctype))
	if pack_doctype == "Shipment":
		return any(row.get("so_detail") for row in get_pack_lines(doc, pack_doctype))
	return False


@frappe.whitelist()
def packing_slip_needs_stock_reservation(packing_slip_name: str) -> bool:
	ps = frappe.get_doc("Packing Slip", packing_slip_name)
	if not uses_pack_stock_reservation(ps, "Packing Slip"):
		return False
	company = get_pack_company(ps, "Packing Slip")
	if not company or get_pack_reserve_mode(company, "Packing Slip") != "Ask":
		return False
	return pack_lines_need_reservation(ps, "Packing Slip")


@frappe.whitelist()
def shipment_needs_stock_reservation(shipment_name: str) -> bool:
	shipment = frappe.get_doc("Shipment", shipment_name)
	if not uses_pack_stock_reservation(shipment, "Shipment"):
		return False
	company = get_pack_company(shipment, "Shipment")
	if not company or get_pack_reserve_mode(company, "Shipment") != "Ask":
		return False
	return pack_lines_need_reservation(shipment, "Shipment")


@frappe.whitelist()
def create_packing_slip_stock_reservation_entries(packing_slip_name: str) -> None:
	ps = frappe.get_doc("Packing Slip", packing_slip_name)
	if ps.docstatus != 1:
		frappe.throw(_("Packing Slip must be submitted"))
	create_stock_reservation_entries_from_pack(ps, "Packing Slip")


@frappe.whitelist()
def cancel_packing_slip_stock_reservation_entries(packing_slip_name: str) -> None:
	cancel_stock_reservation_entries_from_pack("Packing Slip", packing_slip_name)


@frappe.whitelist()
def create_shipment_stock_reservation_entries(shipment_name: str) -> None:
	shipment = frappe.get_doc("Shipment", shipment_name)
	if shipment.docstatus != 1:
		frappe.throw(_("Shipment must be submitted"))
	create_stock_reservation_entries_from_pack(shipment, "Shipment")


@frappe.whitelist()
def cancel_shipment_stock_reservation_entries(shipment_name: str) -> None:
	cancel_stock_reservation_entries_from_pack("Shipment", shipment_name)
