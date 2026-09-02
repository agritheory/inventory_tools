# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import json

import frappe
import pytest
from frappe.contacts.doctype.address.address import get_default_address
from frappe.contacts.doctype.contact.contact import get_default_contact
from frappe.utils import flt, getdate

from erpnext.selling.doctype.sales_order.sales_order import create_pick_list, make_delivery_note
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
from erpnext.stock.doctype.pick_list.pick_list import create_stock_entry

from inventory_tools.inventory_tools.overrides.alternative_sales_workflow import (
	is_alternative_sales_workflow_enabled,
)
from inventory_tools.inventory_tools.overrides.delivery_note import (
	make_delivery_note_from_stock_entry,
)
from inventory_tools.inventory_tools.overrides.packing_slip import (
	make_packing_slip_from_sales_order,
	make_packing_slip_from_stock_entry,
	submit_delivery_note_from_packing_slip,
)
from inventory_tools.inventory_tools.overrides.shipment import (
	make_shipment_from_sales_order,
	make_shipment_from_stock_entry,
	submit_delivery_note_from_shipment,
)

COMPANY = "Ambrosia Pie Company"
CUSTOMER = "Whole Harvest Grocery Group"
ITEM = "Ambrosia Pie"
SOURCE_WAREHOUSE = "Refrigerated Display - APC"
STAGING_WAREHOUSE = "Storeroom - APC"
PIE_RATE = 11.0


def configure_apc_alternative_sales_workflow(enabled: bool):
	settings = frappe.get_doc("Inventory Tools Settings", COMPANY)
	previous = settings.enable_alternative_sales_workflow
	settings.enable_alternative_sales_workflow = 1 if enabled else 0
	settings.save()
	return previous


def restore_apc_alternative_sales_workflow(previous):
	settings = frappe.get_doc("Inventory Tools Settings", COMPANY)
	settings.enable_alternative_sales_workflow = previous
	settings.save()


def save_mapped_doc(doc):
	doc.save()
	return doc.name


def make_test_sales_order(qty=5):
	address = get_default_address("Customer", CUSTOMER)
	so = frappe.new_doc("Sales Order")
	so.company = COMPANY
	so.customer = CUSTOMER
	so.customer_address = address
	so.shipping_address_name = address
	so.contact_person = get_default_contact("Customer", CUSTOMER)
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
	return pl, stock_entry


def assert_against_sales_order(rows, so):
	so_item = so.items[0].name
	for row in rows:
		assert row.against_sales_order == so.name
		assert row.so_detail == so_item


def assert_pick_list_sales_order(locations, so):
	so_item = so.items[0].name
	for location in locations:
		if location.sales_order:
			assert location.sales_order == so.name
			assert location.sales_order_item == so_item


def assert_sales_invoice_sales_order(items, so):
	so_item = so.items[0].name
	for item in items:
		assert item.sales_order == so.name
		assert item.so_detail == so_item


def assert_delivery_note_so_context(dn, so):
	assert dn.customer == so.customer
	assert dn.shipping_address_name == so.shipping_address_name
	assert_against_sales_order(dn.items, so)
	assert flt(dn.items[0].rate, 2) == flt(so.items[0].rate, 2)


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
def test_alternative_sales_workflow_disabled_by_default():
	assert not is_alternative_sales_workflow_enabled(COMPANY)


@pytest.mark.order(92)
def test_alternative_sales_workflow_toggle_off_blocks_mapping():
	previous = configure_apc_alternative_sales_workflow(False)
	try:
		so = make_test_sales_order(qty=2)
		with pytest.raises(frappe.ValidationError):
			make_packing_slip_from_sales_order(so.name)

		dn = make_delivery_note(so.name)
		dn.save()
		assert dn.docstatus == 0
		assert_against_sales_order(dn.items, so)
	finally:
		restore_apc_alternative_sales_workflow(previous)


@pytest.mark.order(93)
def test_alternative_sales_workflow_toggle_off_blocks_delivery_note_from_pack():
	previous = configure_apc_alternative_sales_workflow(True)
	try:
		from inventory_tools.inventory_tools.overrides.delivery_note_from_pack import (
			make_delivery_note_from_packing_slip,
			make_delivery_note_from_shipment,
		)

		so = make_test_sales_order(qty=2)
		ps_name = save_mapped_doc(make_packing_slip_from_sales_order(so.name))
		submit_packing_slip(ps_name)
		shipment_name = save_mapped_doc(make_shipment_from_sales_order(so.name))

		configure_apc_alternative_sales_workflow(False)

		with pytest.raises(frappe.ValidationError):
			make_delivery_note_from_packing_slip(ps_name)
		with pytest.raises(frappe.ValidationError):
			submit_delivery_note_from_packing_slip(ps_name)
		with pytest.raises(frappe.ValidationError):
			make_delivery_note_from_shipment(shipment_name)
		with pytest.raises(frappe.ValidationError):
			submit_delivery_note_from_shipment(shipment_name)
	finally:
		restore_apc_alternative_sales_workflow(previous)


@pytest.mark.order(94)
def test_sales_order_to_packing_slip_without_delivery_note():
	previous = configure_apc_alternative_sales_workflow(True)
	try:
		so = make_test_sales_order(qty=3)

		ps_name = save_mapped_doc(make_packing_slip_from_sales_order(so.name))
		ps = frappe.get_doc("Packing Slip", ps_name)

		assert ps.docstatus == 0
		assert not ps.delivery_note
		assert_against_sales_order(ps.items, so)
	finally:
		restore_apc_alternative_sales_workflow(previous)


@pytest.mark.order(96)
def test_sales_order_to_shipment_without_delivery_note():
	previous = configure_apc_alternative_sales_workflow(True)
	try:
		so = make_test_sales_order(qty=4)

		shipment_name = save_mapped_doc(make_shipment_from_sales_order(so.name))
		shipment = frappe.get_doc("Shipment", shipment_name)

		assert shipment.docstatus == 0
		assert shipment.delivery_address_name
		assert shipment.pickup_address_name
		assert shipment.delivery_contact_name
		assert shipment.delivery_contact_name == so.contact_person
		assert not shipment.delivery_note
		assert len(shipment.shipment_delivery_note) >= 1
		assert all(not row.delivery_note for row in shipment.shipment_delivery_note)
		assert_against_sales_order(shipment.shipment_delivery_note, so)
	finally:
		restore_apc_alternative_sales_workflow(previous)


@pytest.mark.order(98)
def test_stock_entry_to_delivery_note_uses_staging_warehouse():
	previous = configure_apc_alternative_sales_workflow(True)
	try:
		so = make_test_sales_order(qty=2)
		pl, se = make_submitted_material_transfer_stock_entry(so.name)

		dn_name = make_delivery_note_from_stock_entry(se.name)
		dn = frappe.get_doc("Delivery Note", dn_name)

		assert dn.docstatus == 0
		assert all(row.warehouse == STAGING_WAREHOUSE for row in dn.items)
		assert_pick_list_sales_order(pl.locations, so)
		assert_against_sales_order(se.items, so)
		assert_against_sales_order(dn.items, so)
	finally:
		restore_apc_alternative_sales_workflow(previous)


@pytest.mark.order(100)
def test_stock_entry_to_packing_slip_without_delivery_note():
	previous = configure_apc_alternative_sales_workflow(True)
	try:
		so = make_test_sales_order(qty=2)
		pl, se = make_submitted_material_transfer_stock_entry(so.name)

		ps_name = save_mapped_doc(make_packing_slip_from_stock_entry(se.name))
		ps = frappe.get_doc("Packing Slip", ps_name)

		assert ps.docstatus == 0
		assert not ps.delivery_note
		assert all(row.warehouse == STAGING_WAREHOUSE for row in ps.items)
		assert_pick_list_sales_order(pl.locations, so)
		assert_against_sales_order(se.items, so)
		assert_against_sales_order(ps.items, so)
	finally:
		restore_apc_alternative_sales_workflow(previous)


@pytest.mark.order(102)
def test_stock_entry_to_shipment_without_delivery_note():
	previous = configure_apc_alternative_sales_workflow(True)
	try:
		so = make_test_sales_order(qty=2)
		pl, se = make_submitted_material_transfer_stock_entry(so.name)

		shipment_name = save_mapped_doc(make_shipment_from_stock_entry(se.name))
		shipment = frappe.get_doc("Shipment", shipment_name)

		assert shipment.docstatus == 0
		assert shipment.delivery_address_name
		assert shipment.delivery_contact_name
		assert all(not row.delivery_note for row in shipment.shipment_delivery_note)
		assert_pick_list_sales_order(pl.locations, so)
		assert_against_sales_order(se.items, so)
		assert_against_sales_order(shipment.shipment_delivery_note, so)
	finally:
		restore_apc_alternative_sales_workflow(previous)


@pytest.mark.order(105)
def test_packing_slip_delivery_note_mapper_includes_sales_order_context():
	previous = configure_apc_alternative_sales_workflow(True)
	try:
		from inventory_tools.inventory_tools.overrides.delivery_note_from_pack import (
			make_delivery_note_from_packing_slip,
		)

		so = make_test_sales_order(qty=2)
		ps_name = save_mapped_doc(make_packing_slip_from_sales_order(so.name))
		submit_packing_slip(ps_name)

		dn = make_delivery_note_from_packing_slip(ps_name)

		assert dn.docstatus == 0
		assert_delivery_note_so_context(dn, so)
		assert flt(dn.items[0].qty) == 2
		assert dn.items[0].warehouse == SOURCE_WAREHOUSE
	finally:
		restore_apc_alternative_sales_workflow(previous)


@pytest.mark.order(106)
def test_packing_slip_submits_linked_delivery_note():
	"""
	| Account              |  Stock Ledger  |   Debit   |   Credit  |     Party      |
	| -------------------- |:--------------:| ---------:| ---------:| -------------- |
	| Inventory on Hand    |   -2 @ $11.00  |           |    $22.00 |                |
	| Cost of Goods Sold   |                |    $22.00 |           |                |
	"""
	previous = configure_apc_alternative_sales_workflow(True)
	try:
		so = make_test_sales_order(qty=2)
		ps_name = save_mapped_doc(make_packing_slip_from_sales_order(so.name))
		submit_packing_slip(ps_name)
		ps = frappe.get_doc("Packing Slip", ps_name)

		dn_name = submit_delivery_note_from_packing_slip(ps_name)
		dn = frappe.get_doc("Delivery Note", dn_name)

		assert dn.docstatus == 1
		assert_against_sales_order(ps.items, so)
		assert_against_sales_order(dn.items, so)
		assert_delivery_note_so_context(dn, so)
		assert_delivery_note_issue(dn, qty=2, warehouse=SOURCE_WAREHOUSE)
	finally:
		restore_apc_alternative_sales_workflow(previous)


@pytest.mark.order(107)
def test_shipment_delivery_note_mapper_includes_sales_order_context():
	previous = configure_apc_alternative_sales_workflow(True)
	try:
		from inventory_tools.inventory_tools.overrides.delivery_note_from_pack import (
			make_delivery_note_from_shipment,
		)

		so = make_test_sales_order(qty=2)
		shipment_name = save_mapped_doc(make_shipment_from_sales_order(so.name))

		dn = make_delivery_note_from_shipment(shipment_name)

		assert dn.docstatus == 0
		assert_delivery_note_so_context(dn, so)
		assert flt(dn.items[0].qty) == 2
		assert dn.items[0].warehouse == SOURCE_WAREHOUSE
	finally:
		restore_apc_alternative_sales_workflow(previous)


@pytest.mark.order(108)
def test_shipment_submits_linked_delivery_note():
	"""
	| Account              |  Stock Ledger  |   Debit   |   Credit  |     Party      |
	| -------------------- |:--------------:| ---------:| ---------:| -------------- |
	| Inventory on Hand    |   -2 @ $11.00  |           |    $22.00 |                |
	| Cost of Goods Sold   |                |    $22.00 |           |                |
	"""
	previous = configure_apc_alternative_sales_workflow(True)
	try:
		so = make_test_sales_order(qty=2)
		shipment_name = save_mapped_doc(make_shipment_from_sales_order(so.name))
		shipment = frappe.get_doc("Shipment", shipment_name)

		dn_name = submit_delivery_note_from_shipment(shipment_name)
		dn = frappe.get_doc("Delivery Note", dn_name)
		shipment.reload()

		assert dn.docstatus == 1
		assert shipment.delivery_note == dn_name
		assert all(row.delivery_note == dn_name for row in shipment.shipment_delivery_note)
		assert_against_sales_order(shipment.shipment_delivery_note, so)
		assert_against_sales_order(dn.items, so)
		assert_delivery_note_so_context(dn, so)
		assert_delivery_note_issue(dn, qty=2, warehouse=SOURCE_WAREHOUSE)
	finally:
		restore_apc_alternative_sales_workflow(previous)


@pytest.mark.order(110)
def test_vanilla_sales_order_to_invoice_still_works_when_enabled():
	previous = configure_apc_alternative_sales_workflow(True)
	try:
		so = make_test_sales_order(qty=2)

		dn = make_delivery_note(so.name)
		dn.save()
		assert dn.docstatus == 0
		assert_against_sales_order(dn.items, so)

		dn.submit()
		assert_delivery_note_issue(dn, qty=2, warehouse=SOURCE_WAREHOUSE)

		si = make_sales_invoice(dn.name)
		si.save()
		assert si.docstatus == 0
		assert si.items[0].delivery_note == dn.name
		assert_sales_invoice_sales_order(si.items, so)
	finally:
		restore_apc_alternative_sales_workflow(previous)
