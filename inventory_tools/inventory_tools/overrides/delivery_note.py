# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""Alternative Sales Workflow helpers and stock-entry Delivery Note creation."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from frappe.utils import flt

from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote

from inventory_tools.inventory_tools.overrides.alternative_sales_workflow import (
	ensure_alternative_sales_workflow_enabled,
)
from inventory_tools.inventory_tools.overrides.inspection import (
	validate_inspection_with_company_scope,
)


class InventoryToolsDeliveryNote(DeliveryNote):
	def validate_inspection(self):
		validate_inspection_with_company_scope(self)


def apply_customer_delivery_address(dn) -> None:
	address_name = (
		dn.shipping_address_name or dn.customer_address or get_default_address("Customer", dn.customer)
	)
	if not address_name:
		return
	if not dn.shipping_address_name:
		dn.shipping_address_name = address_name
	if not dn.customer_address:
		dn.customer_address = address_name
	if not dn.shipping_address:
		dn.shipping_address = get_address_display(address_name)
	if not dn.address_display:
		dn.address_display = dn.shipping_address


def make_delivery_note_from_stock_entry(stock_entry_name: str) -> str:
	se = frappe.get_doc("Stock Entry", stock_entry_name)
	ensure_alternative_sales_workflow_enabled(se.company)

	if se.docstatus != 1:
		frappe.throw(_("Stock Entry must be submitted"))
	if se.purpose != "Material Transfer":
		frappe.throw(_("Stock Entry purpose must be Material Transfer"))
	if not se.pick_list:
		frappe.throw(_("Stock Entry must be linked to a Pick List"))
	if not se.to_warehouse:
		frappe.throw(_("Stock Entry must have a target warehouse"))

	sales_orders = {row.against_sales_order for row in se.items if row.get("against_sales_order")}
	if not sales_orders:
		frappe.throw(_("Stock Entry has no linked Sales Order"))
	if len(sales_orders) > 1:
		frappe.throw(_("Alternative Sales Workflow supports one Sales Order per Pick List"))

	so_name = next(iter(sales_orders))
	dn = make_delivery_note(so_name)
	apply_customer_delivery_address(dn)
	for item in dn.items:
		item.warehouse = se.to_warehouse
	dn.save()
	return dn.name


def copy_freight_from_pack_to_delivery_note(pack_doc, dn) -> None:
	amount = flt(getattr(pack_doc, "shipment_amount", 0))
	if not amount and pack_doc.doctype == "Shipment":
		amount = get_accepted_shipment_quotation_total(pack_doc.name)
	if not amount:
		return

	for row in dn.taxes:
		if row.charge_type == "Actual" and row.description and "ship" in row.description.lower():
			row.tax_amount = amount
			dn.calculate_taxes_and_totals()
			return

	frappe.msgprint(
		_(
			"Freight amount {0} was not copied onto Delivery Note {1}. "
			"Add an Actual charge row with 'Shipping' in the description, or enter freight manually."
		).format(amount, dn.name),
		indicator="orange",
	)


def get_accepted_shipment_quotation_total(shipment_name: str) -> float:
	if not frappe.db.exists("DocType", "Shipment Quotation"):
		return 0.0

	quotation_name = frappe.db.get_value(
		"Shipment Quotation",
		{"shipment": shipment_name, "docstatus": 1, "status": "Accepted"},
		"name",
	)
	if not quotation_name:
		return 0.0
	return flt(frappe.db.get_value("Shipment Quotation", quotation_name, "grand_total"))
