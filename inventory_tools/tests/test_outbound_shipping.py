# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import json

import frappe
import pytest
from frappe.contacts.doctype.address.address import get_default_address
from frappe.utils import flt, getdate

from erpnext.selling.doctype.sales_order.sales_order import create_pick_list, make_delivery_note
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
from erpnext.stock.doctype.pick_list.pick_list import create_stock_entry

from inventory_tools.inventory_tools.overrides.outbound_shipping import (
	is_outbound_shipping_enabled,
	make_delivery_note_from_stock_entry,
	make_packing_slip_from_sales_order,
	make_packing_slip_from_stock_entry,
	make_shipment_from_sales_order,
	make_shipment_from_stock_entry,
	submit_delivery_note_from_packing_slip,
	submit_delivery_note_from_shipment,
)

COMPANY = "Ambrosia Pie Company"
CUSTOMER = "Whole Harvest Grocery Group"
ITEM = "Ambrosia Pie"
SOURCE_WAREHOUSE = "Refrigerated Display - APC"
STAGING_WAREHOUSE = "Storeroom - APC"
PIE_RATE = 11.0


def configure_apc_outbound_shipping(enabled: bool):
	settings = frappe.get_doc("Inventory Tools Settings", COMPANY)
	previous = settings.enable_sales_order_outbound_shipping
	settings.enable_sales_order_outbound_shipping = 1 if enabled else 0
	settings.save()
	return previous


def restore_apc_outbound_shipping(previous):
	settings = frappe.get_doc("Inventory Tools Settings", COMPANY)
	settings.enable_sales_order_outbound_shipping = previous
	settings.save()


def make_test_sales_order(qty=5):
	address = get_default_address("Customer", CUSTOMER)
	so = frappe.new_doc("Sales Order")
	so.company = COMPANY
	so.customer = CUSTOMER
	so.customer_address = address
	so.shipping_address_name = address
	so.transaction_date = getdate()
	so.delivery_date = getdate()
	so.order_type = "Sales"
	so.currency = "USD"
	so.selling_price_list = "Bakery Wholesale"
	so.append(
		"items",
		{
			"item_code": ITEM,
			"qty": qty,
			"warehouse": SOURCE_WAREHOUSE,
			"delivery_date": getdate(),
		},
	)
	so.save()
	so.submit()
	return so


def make_submitted_material_transfer_stock_entry(so_name):
	pl = create_pick_list(so_name)
	pl.purpose = "Material Transfer"
	for loc in pl.locations:
		loc.picked_qty = loc.qty
	pl.save()
	pl.submit()

	stock_entry = frappe.get_doc(create_stock_entry(json.dumps(pl.as_dict())))
	stock_entry.to_warehouse = STAGING_WAREHOUSE
	for row in stock_entry.items:
		if row.s_warehouse and not row.t_warehouse:
			row.t_warehouse = STAGING_WAREHOUSE
	stock_entry.save()
	stock_entry.submit()
	return stock_entry


def submit_packing_slip(ps_name):
	ps = frappe.get_doc("Packing Slip", ps_name)
	ps.from_case_no = 1
	ps.to_case_no = 1
	ps.save()
	ps.submit()
	return ps


def assert_delivery_note_issue(dn, qty, warehouse):
	"""
	| Account              |  Stock Ledger     |   Debit   |   Credit  |     Party      |
	| -------------------- |:-----------------:| ---------:| ---------:| -------------- |
	| Inventory on Hand    |   -{qty} @ $11.00 |           | qty × $11 |                |
	| Cost of Goods Sold   |                   | qty × $11 |           |                |
	"""
	sle = frappe.get_all(
		"Stock Ledger Entry",
		filters={
			"voucher_type": "Delivery Note",
			"voucher_no": dn.name,
			"item_code": ITEM,
			"is_cancelled": 0,
		},
		fields=["warehouse", "actual_qty", "valuation_rate"],
	)
	assert len(sle) == 1
	assert sle[0].warehouse == warehouse
	assert flt(sle[0].actual_qty) == flt(-qty)
	assert flt(sle[0].valuation_rate, 2) == flt(PIE_RATE, 2)

	gl = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": "Delivery Note", "voucher_no": dn.name, "is_cancelled": 0},
		fields=["account", "debit", "credit"],
	)
	assert gl
	assert flt(sum(row.debit for row in gl), 2) == flt(sum(row.credit for row in gl), 2)
	assert flt(sum(row.credit for row in gl), 2) == flt(qty * PIE_RATE, 2)


@pytest.mark.order(90)
def test_outbound_shipping_disabled_by_default():
	assert not is_outbound_shipping_enabled(COMPANY)


@pytest.mark.order(92)
def test_outbound_shipping_toggle_off_blocks_mapping():
	previous = configure_apc_outbound_shipping(False)
	try:
		so = make_test_sales_order(qty=2)
		with pytest.raises(frappe.ValidationError):
			make_packing_slip_from_sales_order(so.name)

		dn = make_delivery_note(so.name)
		dn.save()
		assert dn.docstatus == 0
		assert dn.items[0].against_sales_order == so.name
	finally:
		restore_apc_outbound_shipping(previous)


@pytest.mark.order(94)
def test_sales_order_to_packing_slip_creates_draft_delivery_note():
	previous = configure_apc_outbound_shipping(True)
	try:
		so = make_test_sales_order(qty=3)

		ps_name = make_packing_slip_from_sales_order(so.name)
		ps = frappe.get_doc("Packing Slip", ps_name)
		dn = frappe.get_doc("Delivery Note", ps.delivery_note)

		assert dn.docstatus == 0
		assert ps.docstatus == 0
		assert dn.items[0].against_sales_order == so.name
	finally:
		restore_apc_outbound_shipping(previous)


@pytest.mark.order(96)
def test_sales_order_to_shipment_uses_draft_delivery_note_not_make_shipment():
	previous = configure_apc_outbound_shipping(True)
	try:
		so = make_test_sales_order(qty=4)

		shipment_name = make_shipment_from_sales_order(so.name)
		shipment = frappe.get_doc("Shipment", shipment_name)
		dn_name = shipment.shipment_delivery_note[0].delivery_note
		dn = frappe.get_doc("Delivery Note", dn_name)

		assert shipment.docstatus == 0
		assert dn.docstatus == 0
		assert shipment.delivery_address_name
		assert len(shipment.shipment_delivery_note) >= 1
	finally:
		restore_apc_outbound_shipping(previous)


@pytest.mark.order(98)
def test_stock_entry_to_delivery_note_uses_staging_warehouse():
	previous = configure_apc_outbound_shipping(True)
	try:
		so = make_test_sales_order(qty=2)
		se = make_submitted_material_transfer_stock_entry(so.name)

		dn_name = make_delivery_note_from_stock_entry(se.name)
		dn = frappe.get_doc("Delivery Note", dn_name)

		assert dn.docstatus == 0
		assert all(row.warehouse == STAGING_WAREHOUSE for row in dn.items)
	finally:
		restore_apc_outbound_shipping(previous)


@pytest.mark.order(100)
def test_stock_entry_to_packing_slip_creates_draft_delivery_note():
	previous = configure_apc_outbound_shipping(True)
	try:
		so = make_test_sales_order(qty=2)
		se = make_submitted_material_transfer_stock_entry(so.name)

		ps_name = make_packing_slip_from_stock_entry(se.name)
		ps = frappe.get_doc("Packing Slip", ps_name)
		dn = frappe.get_doc("Delivery Note", ps.delivery_note)

		assert ps.docstatus == 0
		assert dn.docstatus == 0
		assert all(row.warehouse == STAGING_WAREHOUSE for row in dn.items)
	finally:
		restore_apc_outbound_shipping(previous)


@pytest.mark.order(102)
def test_stock_entry_to_shipment_uses_draft_delivery_note():
	previous = configure_apc_outbound_shipping(True)
	try:
		so = make_test_sales_order(qty=2)
		se = make_submitted_material_transfer_stock_entry(so.name)

		shipment_name = make_shipment_from_stock_entry(se.name)
		shipment = frappe.get_doc("Shipment", shipment_name)
		dn = frappe.get_doc("Delivery Note", shipment.shipment_delivery_note[0].delivery_note)

		assert shipment.docstatus == 0
		assert dn.docstatus == 0
		assert all(row.warehouse == STAGING_WAREHOUSE for row in dn.items)
	finally:
		restore_apc_outbound_shipping(previous)


@pytest.mark.order(104)
def test_packing_slip_submits_linked_delivery_note():
	"""
	| Account              |  Stock Ledger  |   Debit   |   Credit  |     Party      |
	| -------------------- |:--------------:| ---------:| ---------:| -------------- |
	| Inventory on Hand    |   -2 @ $11.00  |           |    $22.00 |                |
	| Cost of Goods Sold   |                |    $22.00 |           |                |
	"""
	previous = configure_apc_outbound_shipping(True)
	try:
		so = make_test_sales_order(qty=2)
		ps_name = make_packing_slip_from_sales_order(so.name)
		submit_packing_slip(ps_name)

		dn_name = submit_delivery_note_from_packing_slip(ps_name)
		dn = frappe.get_doc("Delivery Note", dn_name)

		assert dn.docstatus == 1
		assert_delivery_note_issue(dn, qty=2, warehouse=SOURCE_WAREHOUSE)
	finally:
		restore_apc_outbound_shipping(previous)


@pytest.mark.order(106)
def test_shipment_submits_linked_delivery_note():
	"""
	| Account              |  Stock Ledger  |   Debit   |   Credit  |     Party      |
	| -------------------- |:--------------:| ---------:| ---------:| -------------- |
	| Inventory on Hand    |   -2 @ $11.00  |           |    $22.00 |                |
	| Cost of Goods Sold   |                |    $22.00 |           |                |
	"""
	previous = configure_apc_outbound_shipping(True)
	try:
		so = make_test_sales_order(qty=2)
		shipment_name = make_shipment_from_sales_order(so.name)

		dn_name = submit_delivery_note_from_shipment(shipment_name)
		dn = frappe.get_doc("Delivery Note", dn_name)

		assert dn.docstatus == 1
		assert_delivery_note_issue(dn, qty=2, warehouse=SOURCE_WAREHOUSE)
	finally:
		restore_apc_outbound_shipping(previous)


@pytest.mark.order(108)
def test_vanilla_sales_order_to_invoice_still_works_when_enabled():
	previous = configure_apc_outbound_shipping(True)
	try:
		so = make_test_sales_order(qty=2)

		dn = make_delivery_note(so.name)
		dn.save()
		assert dn.docstatus == 0
		assert dn.items[0].against_sales_order == so.name

		dn.submit()
		assert_delivery_note_issue(dn, qty=2, warehouse=SOURCE_WAREHOUSE)

		si = make_sales_invoice(dn.name)
		si.save()
		assert si.docstatus == 0
		assert si.items[0].delivery_note == dn.name
	finally:
		restore_apc_outbound_shipping(previous)
