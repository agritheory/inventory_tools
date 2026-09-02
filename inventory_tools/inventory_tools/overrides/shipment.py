# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""Alternative Sales Workflow paths for Shipment."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from frappe.contacts.doctype.contact.contact import get_default_contact
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate, nowtime, today

from erpnext.accounts.party import get_party_shipping_address

from inventory_tools.inventory_tools.overrides.alternative_sales_workflow import (
	ensure_alternative_sales_workflow_enabled,
	ensure_alternative_sales_workflow_for_shipment,
)
from inventory_tools.inventory_tools.overrides.delivery_note import (
	copy_freight_from_pack_to_delivery_note,
)
from inventory_tools.inventory_tools.overrides.delivery_note_from_pack import (
	make_delivery_note_from_shipment,
)
from inventory_tools.inventory_tools.overrides.packing_slip import (
	get_single_sales_order_from_stock_entry,
	validate_sales_order_for_pack,
)
from inventory_tools.inventory_tools.overrides.sales_order_identity import (
	stamp_shipment_delivery_notes_from_delivery_note,
)


def resolve_customer_shipping_address(
	customer: str, shipping_address_name: str | None = None
) -> str:
	address_name = (
		shipping_address_name
		or get_party_shipping_address("Customer", customer)
		or get_default_address("Customer", customer)
	)
	if not address_name:
		frappe.throw(
			_("Customer {0} has no shipping address. Add an address before creating a Shipment.").format(
				customer
			),
			title=_("Address Required"),
		)
	return address_name


def resolve_company_pickup_address(company: str) -> str:
	address_name = get_default_address("Company", company)
	if not address_name:
		frappe.throw(
			_("Company {0} has no address. Add a company address before creating a Shipment.").format(
				company
			),
			title=_("Address Required"),
		)
	return address_name


def apply_shipment_pickup_details(shipment, company: str) -> None:
	user = frappe.db.get_value(
		"User",
		frappe.session.user,
		["email", "full_name", "phone", "mobile_no"],
		as_dict=True,
	)
	shipment.pickup_company = shipment.pickup_company or company
	shipment.pickup_from_type = shipment.pickup_from_type or "Company"
	if not shipment.pickup_contact_email:
		shipment.pickup_contact_email = user.email
	if not shipment.pickup_contact:
		pickup_contact_display = user.full_name or ""
		if user.email:
			pickup_contact_display += "<br>" + user.email
		if user.phone:
			pickup_contact_display += "<br>" + user.phone
		elif user.mobile_no:
			pickup_contact_display += "<br>" + user.mobile_no
		shipment.pickup_contact = pickup_contact_display
	if not shipment.pickup_contact_person:
		shipment.pickup_contact_person = frappe.session.user

	if not shipment.pickup_address_name:
		pickup_address_name = resolve_company_pickup_address(company)
		shipment.pickup_address_name = pickup_address_name
		shipment.pickup_address = get_address_display(pickup_address_name)
	shipment.pickup_date = shipment.pickup_date or getdate(today())
	shipment.pickup_from = shipment.pickup_from or nowtime()
	shipment.pickup_to = shipment.pickup_to or "17:00:00"


def apply_shipment_delivery_from_sales_order(shipment, so) -> None:
	address_name = resolve_customer_shipping_address(so.customer, so.shipping_address_name)
	shipment.delivery_customer = so.customer
	shipment.delivery_to_type = shipment.delivery_to_type or "Customer"
	shipment.delivery_address_name = address_name
	shipment.delivery_address = get_address_display(address_name)
	contact_person = so.contact_person or get_default_contact("Customer", so.customer)
	if contact_person:
		shipment.delivery_contact_name = contact_person
		contact = frappe.db.get_value(
			"Contact",
			contact_person,
			["email_id", "phone", "mobile_no", "full_name"],
			as_dict=True,
		)
		delivery_contact_display = so.contact_display or (contact.full_name if contact else "") or ""
		if contact:
			if contact.email_id:
				shipment.delivery_contact_email = contact.email_id
				if contact.email_id not in delivery_contact_display:
					delivery_contact_display += "<br>" + contact.email_id
			if contact.phone:
				if contact.phone not in delivery_contact_display:
					delivery_contact_display += "<br>" + contact.phone
			elif contact.mobile_no:
				if contact.mobile_no not in delivery_contact_display:
					delivery_contact_display += "<br>" + contact.mobile_no
		shipment.delivery_contact = delivery_contact_display
	if not shipment.description_of_content:
		shipment.description_of_content = _("Goods")


def pending_sales_order_item_qty(item) -> float:
	return flt(item.qty) - flt(item.delivered_qty)


def make_shipment_from_sales_order(sales_order_name: str, target_doc=None):
	validate_sales_order_for_pack(sales_order_name)

	def postprocess(source, target):
		apply_shipment_pickup_details(target, source.company)
		apply_shipment_delivery_from_sales_order(target, source)

	def update_shipment_row(source, target, *args):
		pending_qty = pending_sales_order_item_qty(source)
		target.grand_total = flt(source.base_amount or source.amount) or flt(source.rate) * pending_qty
		sdn_meta = frappe.get_meta("Shipment Delivery Note")
		if sdn_meta.has_field("item_code"):
			target.item_code = source.item_code
			target.item_name = source.item_name
			target.qty = pending_qty
			target.stock_uom = source.stock_uom

	shipment = get_mapped_doc(
		"Sales Order",
		sales_order_name,
		{
			"Sales Order": {
				"doctype": "Shipment",
				"field_map": {
					"customer": "delivery_customer",
					"contact_person": "delivery_contact_name",
				},
				"validation": {"docstatus": ["=", 1]},
			},
			"Sales Order Item": {
				"doctype": "Shipment Delivery Note",
				"field_map": {
					"parent": "against_sales_order",
					"name": "so_detail",
				},
				"postprocess": update_shipment_row,
				"condition": lambda item: pending_sales_order_item_qty(item) > 0,
			},
		},
		target_doc,
		postprocess,
	)

	if not shipment.shipment_delivery_note:
		frappe.throw(_("No pending items to ship"))
	return shipment


def make_shipment_from_stock_entry(stock_entry_name: str, target_doc=None):
	se = frappe.get_doc("Stock Entry", stock_entry_name)
	ensure_alternative_sales_workflow_enabled(se.company)
	if se.docstatus != 1:
		frappe.throw(_("Stock Entry must be submitted"))
	if se.purpose != "Material Transfer":
		frappe.throw(_("Stock Entry purpose must be Material Transfer"))
	if not se.pick_list:
		frappe.throw(_("Stock Entry must be linked to a Pick List"))

	so_name = get_single_sales_order_from_stock_entry(se)
	so = frappe.get_doc("Sales Order", so_name)

	def postprocess(source, target):
		apply_shipment_pickup_details(target, se.company)
		apply_shipment_delivery_from_sales_order(target, so)
		if not target.description_of_content:
			target.description_of_content = _("Goods")

	def update_shipment_row(source, target, *args):
		so_item = frappe.db.get_value(
			"Sales Order Item",
			source.so_detail,
			["rate", "base_rate", "amount", "base_amount"],
			as_dict=True,
		)
		amount = flt(so_item.base_amount or so_item.amount) if so_item else 0
		if not amount and so_item:
			amount = flt(so_item.base_rate or so_item.rate) * flt(source.qty)
		target.grand_total = amount
		sdn_meta = frappe.get_meta("Shipment Delivery Note")
		if sdn_meta.has_field("item_code"):
			target.item_code = source.item_code
			target.item_name = source.item_name
			target.qty = source.qty
			target.stock_uom = source.uom

	shipment = get_mapped_doc(
		"Stock Entry",
		stock_entry_name,
		{
			"Stock Entry": {"doctype": "Shipment", "validation": {"docstatus": ["=", 1]}},
			"Stock Entry Detail": {
				"doctype": "Shipment Delivery Note",
				"field_map": {
					"against_sales_order": "against_sales_order",
					"so_detail": "so_detail",
				},
				"postprocess": update_shipment_row,
				"condition": lambda row: row.get("against_sales_order") and row.get("so_detail"),
			},
		},
		target_doc,
		postprocess,
	)

	if not shipment.shipment_delivery_note:
		frappe.throw(_("Stock Entry has no shippable items"))
	return shipment


def make_shipment_from_draft_delivery_note(delivery_note_name: str, target_doc=None):
	"""Build a Shipment from a draft Delivery Note (ERPNext make_shipment requires submitted DN)."""

	def postprocess(source, target):
		apply_shipment_pickup_details(target, source.company)
		address_name = resolve_customer_shipping_address(source.customer, source.shipping_address_name)
		target.delivery_address_name = address_name
		target.delivery_address = (
			source.shipping_address or source.address_display or get_address_display(address_name)
		)
		if source.contact_person:
			contact = frappe.db.get_value(
				"Contact",
				source.contact_person,
				["email_id", "phone", "mobile_no"],
				as_dict=True,
			)
			delivery_contact_display = source.contact_display or ""
			if contact:
				if contact.email_id:
					delivery_contact_display += "<br>" + contact.email_id
				if contact.phone:
					delivery_contact_display += "<br>" + contact.phone
				elif contact.mobile_no:
					delivery_contact_display += "<br>" + contact.mobile_no
			target.delivery_contact = delivery_contact_display
		if not target.description_of_content:
			target.description_of_content = _("Goods")

	shipment = get_mapped_doc(
		"Delivery Note",
		delivery_note_name,
		{
			"Delivery Note": {
				"doctype": "Shipment",
				"field_map": {
					"grand_total": "value_of_goods",
					"company": "pickup_company",
					"company_address": "pickup_address_name",
					"company_address_display": "pickup_address",
					"customer": "delivery_customer",
					"contact_person": "delivery_contact_name",
					"contact_email": "delivery_contact_email",
				},
				"validation": {"docstatus": ["=", 0]},
			},
		},
		target_doc,
		postprocess,
	)

	append_shipment_delivery_note_rows(shipment, delivery_note_name)
	stamp_shipment_delivery_notes_from_delivery_note(shipment)
	return shipment


def append_shipment_delivery_note_rows(shipment, delivery_note_name: str) -> None:
	dn_items = frappe.get_all(
		"Delivery Note Item",
		filters={"parent": delivery_note_name},
		fields=[
			"name",
			"item_code",
			"item_name",
			"qty",
			"stock_uom",
			"base_amount",
			"amount",
			"against_sales_order",
			"so_detail",
		],
	)
	sdn_meta = frappe.get_meta("Shipment Delivery Note")
	has_item_fields = sdn_meta.has_field("dn_detail")
	has_so_fields = sdn_meta.has_field("so_detail")

	for item in dn_items:
		row = {
			"delivery_note": delivery_note_name,
			"grand_total": flt(item.base_amount or item.amount),
		}
		if has_so_fields:
			row.update(
				{
					"against_sales_order": item.against_sales_order,
					"so_detail": item.so_detail,
				}
			)
		if has_item_fields:
			row.update(
				{
					"dn_detail": item.name,
					"item_code": item.item_code,
					"item_name": item.item_name,
					"qty": item.qty,
					"stock_uom": item.stock_uom,
				}
			)
		shipment.append("shipment_delivery_note", row)


def submit_delivery_note_from_shipment(shipment_name: str) -> str:
	ensure_alternative_sales_workflow_for_shipment(shipment_name)
	shipment = frappe.get_doc("Shipment", shipment_name)
	dn = make_delivery_note_from_shipment(shipment_name)
	copy_freight_from_pack_to_delivery_note(shipment, dn)
	dn.save()
	dn.submit()
	return dn.name
