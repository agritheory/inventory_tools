# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import json

import frappe
import pytest
from frappe.utils import getdate

from erpnext.selling.doctype.sales_order.sales_order import create_pick_list
from erpnext.stock.doctype.pick_list.pick_list import create_stock_entry

from inventory_tools.inventory_tools.overrides.outbound_shipping import (
	is_outbound_shipping_enabled,
	make_delivery_note_from_stock_entry,
	make_packing_slip_from_sales_order,
	make_shipment_from_sales_order,
	submit_delivery_note_from_packing_slip,
)

COMPANY = "Ambrosia Pie Company"
CUSTOMER = "Whole Harvest Grocery Group"
ITEM = "Ambrosia Pie"
SOURCE_WAREHOUSE = "Refrigerated Display - APC"
STAGING_WAREHOUSE = "Storeroom - APC"


def configure_apc_outbound_shipping(enabled: bool):
	settings = frappe.get_doc("Inventory Tools Settings", COMPANY)
	settings.enable_sales_order_outbound_shipping = 1 if enabled else 0
	settings.save()


def make_test_sales_order(qty=5):
	so = frappe.new_doc("Sales Order")
	so.company = COMPANY
	so.customer = CUSTOMER
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


@pytest.mark.order(90)
def test_outbound_shipping_disabled_by_default():
	assert not is_outbound_shipping_enabled(COMPANY)


@pytest.mark.order(91)
def test_outbound_shipping_toggle_off_blocks_mapping():
	configure_apc_outbound_shipping(False)
	so = make_test_sales_order(qty=2)
	with pytest.raises(frappe.ValidationError):
		make_packing_slip_from_sales_order(so.name)


@pytest.mark.order(92)
def test_sales_order_to_packing_slip_creates_draft_delivery_note():
	configure_apc_outbound_shipping(True)
	so = make_test_sales_order(qty=3)

	ps_name = make_packing_slip_from_sales_order(so.name)
	ps = frappe.get_doc("Packing Slip", ps_name)
	dn = frappe.get_doc("Delivery Note", ps.delivery_note)

	assert dn.docstatus == 0
	assert ps.docstatus == 0
	assert dn.items[0].against_sales_order == so.name


@pytest.mark.order(93)
def test_sales_order_to_shipment_uses_draft_delivery_note_not_make_shipment():
	configure_apc_outbound_shipping(True)
	so = make_test_sales_order(qty=4)

	shipment_name = make_shipment_from_sales_order(so.name)
	shipment = frappe.get_doc("Shipment", shipment_name)
	dn_name = shipment.shipment_delivery_note[0].delivery_note
	dn = frappe.get_doc("Delivery Note", dn_name)

	assert shipment.docstatus == 0
	assert dn.docstatus == 0
	assert len(shipment.shipment_delivery_note) >= 1


@pytest.mark.order(94)
def test_stock_entry_to_delivery_note_uses_staging_warehouse():
	configure_apc_outbound_shipping(True)
	so = make_test_sales_order(qty=2)
	se = make_submitted_material_transfer_stock_entry(so.name)

	dn_name = make_delivery_note_from_stock_entry(se.name)
	dn = frappe.get_doc("Delivery Note", dn_name)

	assert dn.docstatus == 0
	assert all(row.warehouse == STAGING_WAREHOUSE for row in dn.items)


@pytest.mark.order(95)
def test_packing_slip_submits_linked_delivery_note():
	configure_apc_outbound_shipping(True)
	so = make_test_sales_order(qty=2)
	ps_name = make_packing_slip_from_sales_order(so.name)
	ps = frappe.get_doc("Packing Slip", ps_name)
	ps.from_case_no = 1
	ps.to_case_no = 1
	ps.save()
	ps.submit()

	dn_name = submit_delivery_note_from_packing_slip(ps.name)
	dn = frappe.get_doc("Delivery Note", dn_name)

	assert dn.docstatus == 1


@pytest.mark.order(96)
def test_vanilla_sales_order_to_delivery_note_still_works_when_enabled():
	configure_apc_outbound_shipping(True)
	so = make_test_sales_order(qty=2)

	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

	dn = make_delivery_note(so.name)
	dn.save()

	assert dn.docstatus == 0
	assert dn.items[0].against_sales_order == so.name
