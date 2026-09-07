# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""Alternative Sales Workflow paths for Packing Slip."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, flt

from erpnext.stock.doctype.packing_slip.packing_slip import PackingSlip
from erpnext.utilities.transaction_base import validate_uom_is_integer

from inventory_tools.inventory_tools.overrides.alternative_sales_workflow import (
	ensure_alternative_sales_workflow_enabled,
	ensure_alternative_sales_workflow_for_packing_slip,
	is_alternative_sales_workflow_enabled,
)
from inventory_tools.inventory_tools.overrides.delivery_note import (
	copy_freight_from_pack_to_delivery_note,
)
from inventory_tools.inventory_tools.overrides.delivery_note_from_pack import (
	make_delivery_note_from_packing_slip,
)

SALES_ORDER_TO_PACKING_SLIP_ITEM_MAP = {
	"item_code": "item_code",
	"item_name": "item_name",
	"stock_uom": "stock_uom",
	"parent": "against_sales_order",
	"name": "so_detail",
}

STOCK_ENTRY_TO_PACKING_SLIP_ITEM_MAP = {
	"item_code": "item_code",
	"item_name": "item_name",
	"uom": "stock_uom",
	"qty": "qty",
	"against_sales_order": "against_sales_order",
	"so_detail": "so_detail",
}


class InventoryToolsPackingSlip(PackingSlip):
	def _validate_mandatory(self):  # nosemgrep: no-underscore-prefix-function
		if self.uses_alternative_sales_workflow_without_delivery_note():
			previous = self.flags.ignore_mandatory
			self.flags.ignore_mandatory = True
			try:
				super()._validate_mandatory()
			finally:
				self.flags.ignore_mandatory = previous
			return
		super()._validate_mandatory()

	def validate(self) -> None:
		if self.uses_alternative_sales_workflow_without_delivery_note():
			self.validate_alternative_sales_workflow()
			return
		super().validate()

	def on_submit(self):
		if self.uses_alternative_sales_workflow_without_delivery_note():
			super().on_submit()
			from inventory_tools.inventory_tools.overrides.pack_stock_reservation import (
				maybe_reserve_stock_on_pack_submit,
			)

			maybe_reserve_stock_on_pack_submit(self, "Packing Slip")
			if self.get("reserve_stock_on_submit"):
				self.db_set("reserve_stock_on_submit", 0)
			return
		if self.delivery_note:
			super().on_submit()

	def on_cancel(self):
		if self.uses_alternative_sales_workflow_without_delivery_note():
			from inventory_tools.inventory_tools.overrides.pack_stock_reservation import (
				cancel_stock_reservation_entries_from_pack,
			)

			cancel_stock_reservation_entries_from_pack("Packing Slip", self.name, notify=False)
		if self.delivery_note or self.uses_alternative_sales_workflow_without_delivery_note():
			super().on_cancel()

	def validate_case_nos(self):
		if self.uses_alternative_sales_workflow_without_delivery_note():
			if cint(self.from_case_no) <= 0:
				self.from_case_no = 1
			if not self.to_case_no:
				self.to_case_no = self.from_case_no
			elif cint(self.to_case_no) < cint(self.from_case_no):
				frappe.throw(_("'To Package No.' cannot be less than 'From Package No.'"))
			return
		super().validate_case_nos()

	def onload(self):
		from inventory_tools.inventory_tools.overrides.pack_stock_reservation import (
			has_pack_originated_reservation,
			is_stock_reservation_enabled,
			pack_lines_need_reservation,
			uses_pack_stock_reservation,
		)

		if not is_stock_reservation_enabled() or not uses_pack_stock_reservation(self, "Packing Slip"):
			return

		if pack_lines_need_reservation(self, "Packing Slip"):
			self.set_onload("has_unreserved_pack_stock", True)
		if has_pack_originated_reservation("Packing Slip", self.name):
			self.set_onload("has_pack_reserved_stock", True)

	def uses_alternative_sales_workflow_without_delivery_note(self) -> bool:
		if self.delivery_note:
			return False
		if not any(item.get("so_detail") for item in self.get("items") or []):
			return False
		company = self.get_alternative_sales_workflow_company()
		return bool(company and is_alternative_sales_workflow_enabled(company))

	def get_alternative_sales_workflow_company(self) -> str | None:
		for item in self.get("items") or []:
			if item.against_sales_order:
				return frappe.db.get_value("Sales Order", item.against_sales_order, "company")
		return None

	def validate_alternative_sales_workflow(self) -> None:
		self.validate_case_nos()
		self.validate_alternative_sales_workflow_items()
		validate_uom_is_integer(self, "stock_uom", "qty")
		validate_uom_is_integer(self, "weight_uom", "net_weight")
		self.set_missing_values()
		self.calculate_net_total_pkg()

	def validate_alternative_sales_workflow_items(self) -> None:
		for item in self.items:
			if item.qty <= 0:
				frappe.throw(_("Row {0}: Qty must be greater than 0.").format(item.idx))
			if not item.so_detail:
				frappe.throw(_("Row {0}: Sales Order Item reference is required.").format(item.idx))

			so_item_qty = frappe.db.get_value(
				"Sales Order Item",
				item.so_detail,
				["qty", "delivered_qty"],
				as_dict=True,
			)
			if not so_item_qty:
				frappe.throw(_("Row {0}: Please provide a valid Sales Order Item reference.").format(item.idx))
			remaining_qty = flt(so_item_qty.qty) - flt(so_item_qty.delivered_qty)
			if remaining_qty <= 0:
				frappe.throw(
					_("Row {0}: Delivery Note is already completed for Item {1}.").format(
						item.idx, frappe.bold(item.item_code)
					)
				)
			if item.qty > remaining_qty:
				frappe.throw(
					_("Row {0}: Qty cannot be greater than {1} for the Item {2}.").format(
						item.idx, frappe.bold(remaining_qty), frappe.bold(item.item_code)
					)
				)


def get_single_sales_order_from_stock_entry(stock_entry) -> str:
	sales_orders = {
		row.against_sales_order for row in stock_entry.items if row.get("against_sales_order")
	}
	if not sales_orders:
		frappe.throw(_("Stock Entry has no linked Sales Order"))
	if len(sales_orders) > 1:
		frappe.throw(_("Alternative Sales Workflow supports one Sales Order per Pick List"))
	return next(iter(sales_orders))


def validate_sales_order_for_pack(sales_order_name: str):
	so = frappe.get_doc("Sales Order", sales_order_name)
	ensure_alternative_sales_workflow_enabled(so.company)
	if so.docstatus != 1:
		frappe.throw(_("Sales Order must be submitted"))
	if so.status in ("Closed", "Completed"):
		frappe.throw(_("Sales Order is closed or completed"))
	return so


def pending_sales_order_item_qty(item) -> float:
	return flt(item.qty) - flt(item.delivered_qty)


def update_packing_slip_item_from_sales_order_item(source, target, *args) -> None:
	target.qty = pending_sales_order_item_qty(source)


def set_packing_slip_missing_values(source, target) -> None:
	target.run_method("set_missing_values")


def make_packing_slip_from_sales_order(sales_order_name: str, target_doc=None):
	validate_sales_order_for_pack(sales_order_name)

	packing_slip = get_mapped_doc(
		"Sales Order",
		sales_order_name,
		{
			"Sales Order": {
				"doctype": "Packing Slip",
				"validation": {"docstatus": ["=", 1]},
			},
			"Sales Order Item": {
				"doctype": "Packing Slip Item",
				"field_map": SALES_ORDER_TO_PACKING_SLIP_ITEM_MAP,
				"postprocess": update_packing_slip_item_from_sales_order_item,
				"condition": lambda item: pending_sales_order_item_qty(item) > 0,
			},
		},
		target_doc,
		set_packing_slip_missing_values,
	)

	if not packing_slip.items:
		frappe.throw(_("No pending items to pack"))
	return packing_slip


def update_packing_slip_item_from_stock_entry_detail(source, target, *args) -> None:
	target.qty = flt(source.qty)


def make_packing_slip_from_stock_entry(stock_entry_name: str, target_doc=None):
	se = frappe.get_doc("Stock Entry", stock_entry_name)
	ensure_alternative_sales_workflow_enabled(se.company)
	if se.docstatus != 1:
		frappe.throw(_("Stock Entry must be submitted"))
	if se.purpose != "Material Transfer":
		frappe.throw(_("Stock Entry purpose must be Material Transfer"))
	if not se.pick_list:
		frappe.throw(_("Stock Entry must be linked to a Pick List"))
	get_single_sales_order_from_stock_entry(se)

	packing_slip = get_mapped_doc(
		"Stock Entry",
		stock_entry_name,
		{
			"Stock Entry": {"doctype": "Packing Slip", "validation": {"docstatus": ["=", 1]}},
			"Stock Entry Detail": {
				"doctype": "Packing Slip Item",
				"field_map": STOCK_ENTRY_TO_PACKING_SLIP_ITEM_MAP,
				"postprocess": update_packing_slip_item_from_stock_entry_detail,
				"condition": lambda row: row.get("against_sales_order") and row.get("so_detail"),
			},
		},
		target_doc,
		set_packing_slip_missing_values,
	)

	if not packing_slip.items:
		frappe.throw(_("Stock Entry has no packable items"))
	return packing_slip


def submit_delivery_note_from_packing_slip(packing_slip_name: str) -> str:
	ensure_alternative_sales_workflow_for_packing_slip(packing_slip_name)
	ps = frappe.get_doc("Packing Slip", packing_slip_name)
	dn = make_delivery_note_from_packing_slip(packing_slip_name)
	copy_freight_from_pack_to_delivery_note(ps, dn)
	dn.save()
	dn.submit()
	return dn.name
