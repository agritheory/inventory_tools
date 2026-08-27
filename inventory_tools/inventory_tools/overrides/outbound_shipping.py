# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""Additive outbound shipping paths (Sales Order / staging Stock Entry → pack → Delivery Note)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate, nowtime, today

from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from erpnext.stock.doctype.delivery_note.delivery_note import make_packing_slip


def is_outbound_shipping_enabled(company: str | None) -> bool:
	if not company:
		return False
	return bool(
		frappe.db.get_value(
			"Inventory Tools Settings",
			company,
			"enable_sales_order_outbound_shipping",
		)
	)


def ensure_outbound_shipping_enabled(company: str) -> None:
	if not is_outbound_shipping_enabled(company):
		frappe.throw(
			_("Sales Order outbound shipping is not enabled for {0}").format(company),
			title=_("Outbound Shipping Disabled"),
		)


def save_draft_delivery_note_from_sales_order(
	sales_order_name: str,
) -> frappe.model.document.Document:
	so = frappe.get_doc("Sales Order", sales_order_name)
	ensure_outbound_shipping_enabled(so.company)

	if so.docstatus != 1:
		frappe.throw(_("Sales Order must be submitted"))
	if so.status in ("Closed", "Completed"):
		frappe.throw(_("Sales Order is closed or completed"))

	dn = make_delivery_note(sales_order_name)
	dn.save()
	return dn


def make_packing_slip_from_sales_order(sales_order_name: str):
	dn = save_draft_delivery_note_from_sales_order(sales_order_name)
	ps = make_packing_slip(dn.name)
	ps.save()
	return ps.name


def make_shipment_from_sales_order(sales_order_name: str):
	dn = save_draft_delivery_note_from_sales_order(sales_order_name)
	shipment = make_shipment_from_draft_delivery_note(dn.name)
	shipment.save()
	return shipment.name


def make_delivery_note_from_stock_entry(stock_entry_name: str):
	se = frappe.get_doc("Stock Entry", stock_entry_name)
	ensure_outbound_shipping_enabled(se.company)

	if se.docstatus != 1:
		frappe.throw(_("Stock Entry must be submitted"))
	if se.purpose != "Material Transfer":
		frappe.throw(_("Stock Entry purpose must be Material Transfer"))
	if not se.pick_list:
		frappe.throw(_("Stock Entry must be linked to a Pick List"))
	if not se.to_warehouse:
		frappe.throw(_("Stock Entry must have a target warehouse"))

	pick_list = frappe.get_doc("Pick List", se.pick_list)
	sales_orders = {loc.sales_order for loc in pick_list.locations if loc.sales_order}
	if not sales_orders:
		frappe.throw(_("Pick List has no linked Sales Order"))
	if len(sales_orders) > 1:
		frappe.throw(_("Stock Entry outbound shipping supports one Sales Order per Pick List"))

	so_name = next(iter(sales_orders))
	dn = make_delivery_note(so_name)
	for item in dn.items:
		item.warehouse = se.to_warehouse
	dn.save()
	return dn.name


def make_packing_slip_from_stock_entry(stock_entry_name: str):
	dn_name = make_delivery_note_from_stock_entry(stock_entry_name)
	ps = make_packing_slip(dn_name)
	ps.save()
	return ps.name


def make_shipment_from_stock_entry(stock_entry_name: str):
	dn_name = make_delivery_note_from_stock_entry(stock_entry_name)
	shipment = make_shipment_from_draft_delivery_note(dn_name)
	shipment.save()
	return shipment.name


def submit_delivery_note_from_packing_slip(packing_slip_name: str):
	ps = frappe.get_doc("Packing Slip", packing_slip_name)
	dn = get_draft_delivery_note_for_pack(ps)
	ensure_outbound_shipping_enabled(dn.company)
	copy_freight_from_pack_to_delivery_note(ps, dn)
	dn.save()
	dn.submit()
	return dn.name


def submit_delivery_note_from_shipment(shipment_name: str):
	shipment = frappe.get_doc("Shipment", shipment_name)
	company = shipment.pickup_company or frappe.defaults.get_user_default("Company")
	ensure_outbound_shipping_enabled(company)
	dn = get_draft_delivery_note_for_pack(shipment)
	copy_freight_from_pack_to_delivery_note(shipment, dn)
	dn.save()
	dn.submit()
	return dn.name


@frappe.whitelist()
def make_packing_slip_from_sales_order_whitelisted(sales_order_name: str):
	return make_packing_slip_from_sales_order(sales_order_name)


@frappe.whitelist()
def make_shipment_from_sales_order_whitelisted(sales_order_name: str):
	return make_shipment_from_sales_order(sales_order_name)


@frappe.whitelist()
def make_delivery_note_from_stock_entry_whitelisted(stock_entry_name: str):
	return make_delivery_note_from_stock_entry(stock_entry_name)


@frappe.whitelist()
def make_packing_slip_from_stock_entry_whitelisted(stock_entry_name: str):
	return make_packing_slip_from_stock_entry(stock_entry_name)


@frappe.whitelist()
def make_shipment_from_stock_entry_whitelisted(stock_entry_name: str):
	return make_shipment_from_stock_entry(stock_entry_name)


@frappe.whitelist()
def submit_delivery_note_from_packing_slip_whitelisted(packing_slip_name: str):
	return submit_delivery_note_from_packing_slip(packing_slip_name)


@frappe.whitelist()
def submit_delivery_note_from_shipment_whitelisted(shipment_name: str):
	return submit_delivery_note_from_shipment(shipment_name)


def get_draft_delivery_note_for_pack(pack_doc):
	dn_name = None
	if pack_doc.doctype == "Packing Slip":
		dn_name = pack_doc.delivery_note
	elif pack_doc.doctype == "Shipment":
		for row in pack_doc.shipment_delivery_note or []:
			if row.delivery_note:
				dn_name = row.delivery_note
				break

	if not dn_name:
		frappe.throw(_("No Delivery Note is linked to this document"))

	dn = frappe.get_doc("Delivery Note", dn_name)
	if dn.docstatus != 0:
		frappe.throw(_("Linked Delivery Note {0} is not a draft").format(dn.name))
	return dn


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


def make_shipment_from_draft_delivery_note(delivery_note_name: str, target_doc=None):
	"""Build a Shipment from a draft Delivery Note (ERPNext make_shipment requires submitted DN)."""

	def postprocess(source, target):
		user = frappe.db.get_value(
			"User",
			frappe.session.user,
			["email", "full_name", "phone", "mobile_no"],
			as_dict=True,
		)
		target.pickup_contact_email = user.email
		pickup_contact_display = user.full_name or ""
		if user.email:
			pickup_contact_display += "<br>" + user.email
		if user.phone:
			pickup_contact_display += "<br>" + user.phone
		elif user.mobile_no:
			pickup_contact_display += "<br>" + user.mobile_no
		target.pickup_contact = pickup_contact_display
		target.pickup_contact_person = frappe.session.user

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

		if source.shipping_address_name:
			target.delivery_address_name = source.shipping_address_name
			target.delivery_address = source.shipping_address
		elif source.customer_address:
			target.delivery_address_name = source.customer_address
			target.delivery_address = source.address_display

		target.pickup_date = target.pickup_date or getdate(today())
		target.pickup_from = target.pickup_from or nowtime()
		target.pickup_to = target.pickup_to or "17:00:00"
		target.pickup_from_type = target.pickup_from_type or "Company"
		target.delivery_to_type = target.delivery_to_type or "Customer"
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
	return shipment


def append_shipment_delivery_note_rows(shipment, delivery_note_name: str) -> None:
	dn_items = frappe.get_all(
		"Delivery Note Item",
		filters={"parent": delivery_note_name},
		fields=["name", "item_code", "item_name", "qty", "stock_uom", "base_amount", "amount"],
	)
	sdn_meta = frappe.get_meta("Shipment Delivery Note")
	has_item_fields = sdn_meta.has_field("dn_detail")

	for item in dn_items:
		row = {
			"delivery_note": delivery_note_name,
			"grand_total": flt(item.base_amount or item.amount),
		}
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
