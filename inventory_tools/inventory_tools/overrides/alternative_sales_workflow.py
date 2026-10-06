# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""Inventory Tools Settings gate for Alternative Sales Workflow."""

from __future__ import annotations

import frappe
from frappe import _


def is_alternative_sales_workflow_enabled(company: str | None) -> bool:
	if not company:
		return False
	return bool(
		frappe.db.get_value(
			"Inventory Tools Settings",
			company,
			"enable_alternative_sales_workflow",
		)
	)


def ensure_alternative_sales_workflow_enabled(company: str) -> None:
	if not is_alternative_sales_workflow_enabled(company):
		frappe.throw(
			_("Alternative Sales Workflow is not enabled for {0}").format(company),
			title=_("Alternative Sales Workflow Disabled"),
		)


def get_company_for_packing_slip(packing_slip_name: str) -> str:
	ps = frappe.get_doc("Packing Slip", packing_slip_name)
	if ps.delivery_note:
		company = frappe.db.get_value("Delivery Note", ps.delivery_note, "company")
		if company:
			return company

	for item in ps.get("items") or []:
		if item.against_sales_order:
			return frappe.db.get_value("Sales Order", item.against_sales_order, "company")

	return frappe.throw(
		_("Could not determine company for Packing Slip {0}").format(packing_slip_name)
	)


def get_company_for_shipment(shipment_name: str) -> str:
	shipment = frappe.get_doc("Shipment", shipment_name)
	if shipment.pickup_company:
		return shipment.pickup_company

	if shipment.get("delivery_note"):
		company = frappe.db.get_value("Delivery Note", shipment.delivery_note, "company")
		if company:
			return company

	for row in shipment.get("shipment_delivery_note") or []:
		if row.delivery_note:
			company = frappe.db.get_value("Delivery Note", row.delivery_note, "company")
			if company:
				return company
		if row.against_sales_order:
			return frappe.db.get_value("Sales Order", row.against_sales_order, "company")

	return frappe.throw(_("Could not determine company for Shipment {0}").format(shipment_name))


def ensure_alternative_sales_workflow_for_packing_slip(packing_slip_name: str) -> None:
	ensure_alternative_sales_workflow_enabled(get_company_for_packing_slip(packing_slip_name))


def ensure_alternative_sales_workflow_for_shipment(shipment_name: str) -> None:
	ensure_alternative_sales_workflow_enabled(get_company_for_shipment(shipment_name))


@frappe.whitelist()
def make_packing_slip_from_sales_order_whitelisted(sales_order_name: str, target_doc=None):
	from inventory_tools.inventory_tools.overrides.packing_slip import (
		make_packing_slip_from_sales_order,
	)

	return make_packing_slip_from_sales_order(sales_order_name, target_doc)


@frappe.whitelist()
def make_shipment_from_sales_order_whitelisted(sales_order_name: str, target_doc=None):
	from inventory_tools.inventory_tools.overrides.shipment import make_shipment_from_sales_order

	return make_shipment_from_sales_order(sales_order_name, target_doc)


@frappe.whitelist()
def make_delivery_note_from_stock_entry_whitelisted(stock_entry_name: str):
	from inventory_tools.inventory_tools.overrides.delivery_note import (
		make_delivery_note_from_stock_entry,
	)

	return make_delivery_note_from_stock_entry(stock_entry_name)


@frappe.whitelist()
def make_packing_slip_from_stock_entry_whitelisted(stock_entry_name: str, target_doc=None):
	from inventory_tools.inventory_tools.overrides.packing_slip import (
		make_packing_slip_from_stock_entry,
	)

	return make_packing_slip_from_stock_entry(stock_entry_name, target_doc)


@frappe.whitelist()
def make_shipment_from_stock_entry_whitelisted(stock_entry_name: str, target_doc=None):
	from inventory_tools.inventory_tools.overrides.shipment import make_shipment_from_stock_entry

	return make_shipment_from_stock_entry(stock_entry_name, target_doc)


@frappe.whitelist()
def submit_delivery_note_from_packing_slip_whitelisted(packing_slip_name: str):
	from inventory_tools.inventory_tools.overrides.packing_slip import (
		submit_delivery_note_from_packing_slip,
	)

	return submit_delivery_note_from_packing_slip(packing_slip_name)


@frappe.whitelist()
def submit_delivery_note_from_shipment_whitelisted(shipment_name: str):
	from inventory_tools.inventory_tools.overrides.shipment import submit_delivery_note_from_shipment

	return submit_delivery_note_from_shipment(shipment_name)


@frappe.whitelist()
def make_delivery_note_from_packing_slip_whitelisted(packing_slip_name: str):
	from inventory_tools.inventory_tools.overrides.delivery_note_from_pack import (
		make_delivery_note_from_packing_slip,
	)

	ensure_alternative_sales_workflow_for_packing_slip(packing_slip_name)
	dn = make_delivery_note_from_packing_slip(packing_slip_name)
	return dn.name


@frappe.whitelist()
def make_delivery_note_from_shipment_whitelisted(shipment_name: str):
	from inventory_tools.inventory_tools.overrides.delivery_note_from_pack import (
		make_delivery_note_from_shipment,
	)

	ensure_alternative_sales_workflow_for_shipment(shipment_name)
	dn = make_delivery_note_from_shipment(shipment_name)
	return dn.name
