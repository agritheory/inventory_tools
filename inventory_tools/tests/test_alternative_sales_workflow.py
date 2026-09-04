# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import json

import frappe
import pytest
from frappe.contacts.doctype.address.address import get_default_address
from frappe.contacts.doctype.contact.contact import get_default_contact
from frappe.utils import cint, flt, getdate

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
		assert all(row.t_warehouse == STAGING_WAREHOUSE for row in se.items)
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


def configure_stock_reservation(enabled: bool):
	previous = cint(frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"))
	frappe.db.set_single_value("Stock Settings", "enable_stock_reservation", 1 if enabled else 0)
	return previous


def restore_stock_reservation(previous):
	frappe.db.set_single_value("Stock Settings", "enable_stock_reservation", previous)


def configure_pack_reserve_modes(packing_slip_mode="Always", shipment_mode="Ask"):
	settings = frappe.get_doc("Inventory Tools Settings", COMPANY)
	previous = (
		settings.reserve_stock_on_packing_slip,
		settings.reserve_stock_on_shipment,
	)
	settings.reserve_stock_on_packing_slip = packing_slip_mode
	settings.reserve_stock_on_shipment = shipment_mode
	settings.save()
	return previous


def restore_pack_reserve_modes(previous):
	ps_mode, sh_mode = previous
	settings = frappe.get_doc("Inventory Tools Settings", COMPANY)
	settings.reserve_stock_on_packing_slip = ps_mode
	settings.reserve_stock_on_shipment = sh_mode
	settings.save()


def make_test_sales_order_with_reserve(qty=5):
	so = make_test_sales_order(qty)
	frappe.db.set_value("Sales Order Item", so.items[0].name, "reserve_stock", 1)
	so.reload()
	return so


def add_shipment_parcel(shipment):
	shipment.append(
		"shipment_parcel",
		{"length": 5, "width": 5, "height": 5, "weight": 5, "count": 1},
	)
	shipment.save()
	return shipment


def submit_shipment(shipment_name):
	shipment = frappe.get_doc("Shipment", shipment_name)
	if not shipment.shipment_parcel:
		add_shipment_parcel(shipment)
	shipment.submit()
	return shipment


def get_pack_sres(pack_doctype, pack_name):
	return frappe.get_all(
		"Stock Reservation Entry",
		filters={
			"pack_from_doctype": pack_doctype,
			"pack_from_name": pack_name,
			"docstatus": 1,
		},
		pluck="name",
	)


@pytest.mark.order(112)
def test_packing_slip_always_creates_stock_reservation_on_submit():
	previous_alt = configure_apc_alternative_sales_workflow(True)
	previous_reservation = configure_stock_reservation(True)
	previous_modes = configure_pack_reserve_modes("Always", "Ask")
	try:
		so = make_test_sales_order_with_reserve(qty=2)
		ps_name = save_mapped_doc(make_packing_slip_from_sales_order(so.name))
		submit_packing_slip(ps_name)

		sres = get_pack_sres("Packing Slip", ps_name)
		assert len(sres) == 1
		assert frappe.db.get_value("Stock Reservation Entry", sres[0], "warehouse") == SOURCE_WAREHOUSE
	finally:
		restore_pack_reserve_modes(previous_modes)
		restore_stock_reservation(previous_reservation)
		restore_apc_alternative_sales_workflow(previous_alt)


@pytest.mark.order(114)
def test_packing_slip_ask_skips_reservation_without_confirm():
	previous_alt = configure_apc_alternative_sales_workflow(True)
	previous_reservation = configure_stock_reservation(True)
	previous_modes = configure_pack_reserve_modes("Ask", "Ask")
	try:
		from inventory_tools.inventory_tools.overrides.pack_stock_reservation import (
			packing_slip_needs_stock_reservation,
		)

		so = make_test_sales_order_with_reserve(qty=2)
		ps_name = save_mapped_doc(make_packing_slip_from_sales_order(so.name))
		assert packing_slip_needs_stock_reservation(ps_name)
		submit_packing_slip(ps_name)

		assert not get_pack_sres("Packing Slip", ps_name)
	finally:
		restore_pack_reserve_modes(previous_modes)
		restore_stock_reservation(previous_reservation)
		restore_apc_alternative_sales_workflow(previous_alt)


@pytest.mark.order(116)
def test_packing_slip_ask_reserves_when_flag_set():
	previous_alt = configure_apc_alternative_sales_workflow(True)
	previous_reservation = configure_stock_reservation(True)
	previous_modes = configure_pack_reserve_modes("Ask", "Ask")
	try:
		so = make_test_sales_order_with_reserve(qty=2)
		ps_name = save_mapped_doc(make_packing_slip_from_sales_order(so.name))
		ps = frappe.get_doc("Packing Slip", ps_name)
		ps.reserve_stock_on_submit = 1
		ps.from_case_no = 1
		ps.to_case_no = 1
		ps.save()
		ps.submit()

		assert len(get_pack_sres("Packing Slip", ps_name)) == 1
	finally:
		restore_pack_reserve_modes(previous_modes)
		restore_stock_reservation(previous_reservation)
		restore_apc_alternative_sales_workflow(previous_alt)


@pytest.mark.order(118)
def test_pick_list_reservation_skips_packing_slip_ask():
	previous_alt = configure_apc_alternative_sales_workflow(True)
	previous_reservation = configure_stock_reservation(True)
	previous_modes = configure_pack_reserve_modes("Ask", "Ask")
	try:
		from inventory_tools.inventory_tools.overrides.pack_stock_reservation import (
			packing_slip_needs_stock_reservation,
		)

		so = make_test_sales_order_with_reserve(qty=2)
		pl = create_pick_list(so.name)
		for loc in pl.locations:
			loc.picked_qty = loc.qty
		pl.save()
		pl.submit()
		pl.create_stock_reservation_entries()

		ps_name = save_mapped_doc(make_packing_slip_from_sales_order(so.name))
		assert not packing_slip_needs_stock_reservation(ps_name)
		submit_packing_slip(ps_name)
		assert not get_pack_sres("Packing Slip", ps_name)
	finally:
		restore_pack_reserve_modes(previous_modes)
		restore_stock_reservation(previous_reservation)
		restore_apc_alternative_sales_workflow(previous_alt)


@pytest.mark.order(120)
def test_shipment_never_skips_stock_reservation():
	previous_alt = configure_apc_alternative_sales_workflow(True)
	previous_reservation = configure_stock_reservation(True)
	previous_modes = configure_pack_reserve_modes("Always", "Never")
	try:
		so = make_test_sales_order_with_reserve(qty=2)
		shipment_name = save_mapped_doc(make_shipment_from_sales_order(so.name))
		submit_shipment(shipment_name)

		assert not get_pack_sres("Shipment", shipment_name)
	finally:
		restore_pack_reserve_modes(previous_modes)
		restore_stock_reservation(previous_reservation)
		restore_apc_alternative_sales_workflow(previous_alt)


@pytest.mark.order(122)
def test_shipment_ask_quote_path_submits_without_reservation():
	previous_alt = configure_apc_alternative_sales_workflow(True)
	previous_reservation = configure_stock_reservation(True)
	previous_modes = configure_pack_reserve_modes("Always", "Ask")
	try:
		from inventory_tools.inventory_tools.overrides.pack_stock_reservation import (
			shipment_needs_stock_reservation,
		)

		so = make_test_sales_order_with_reserve(qty=2)
		shipment_name = save_mapped_doc(make_shipment_from_sales_order(so.name))
		assert shipment_needs_stock_reservation(shipment_name)
		submit_shipment(shipment_name)

		assert not get_pack_sres("Shipment", shipment_name)
	finally:
		restore_pack_reserve_modes(previous_modes)
		restore_stock_reservation(previous_reservation)
		restore_apc_alternative_sales_workflow(previous_alt)


@pytest.mark.order(124)
def test_delivery_note_from_pack_uses_sre_warehouse():
	previous_alt = configure_apc_alternative_sales_workflow(True)
	previous_reservation = configure_stock_reservation(True)
	previous_modes = configure_pack_reserve_modes("Always", "Ask")
	try:
		from inventory_tools.inventory_tools.overrides.delivery_note_from_pack import (
			make_delivery_note_from_packing_slip,
		)

		so = make_test_sales_order_with_reserve(qty=2)
		ps_name = save_mapped_doc(make_packing_slip_from_sales_order(so.name))
		submit_packing_slip(ps_name)

		sres = get_pack_sres("Packing Slip", ps_name)
		assert len(sres) == 1
		reserved_warehouse = frappe.db.get_value("Stock Reservation Entry", sres[0], "warehouse")
		assert reserved_warehouse == SOURCE_WAREHOUSE

		dn = make_delivery_note_from_packing_slip(ps_name)
		assert dn.items[0].warehouse == reserved_warehouse
	finally:
		restore_pack_reserve_modes(previous_modes)
		restore_stock_reservation(previous_reservation)
		restore_apc_alternative_sales_workflow(previous_alt)


@pytest.mark.order(126)
def test_packing_slip_cancel_cancels_pack_stock_reservation():
	previous_alt = configure_apc_alternative_sales_workflow(True)
	previous_reservation = configure_stock_reservation(True)
	previous_modes = configure_pack_reserve_modes("Always", "Ask")
	try:
		so = make_test_sales_order_with_reserve(qty=2)
		ps_name = save_mapped_doc(make_packing_slip_from_sales_order(so.name))
		submit_packing_slip(ps_name)
		assert len(get_pack_sres("Packing Slip", ps_name)) == 1

		ps = frappe.get_doc("Packing Slip", ps_name)
		ps.cancel()
		assert not get_pack_sres("Packing Slip", ps_name)
	finally:
		restore_pack_reserve_modes(previous_modes)
		restore_stock_reservation(previous_reservation)
		restore_apc_alternative_sales_workflow(previous_alt)
