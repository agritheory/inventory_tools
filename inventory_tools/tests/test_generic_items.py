# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from frappe.utils import flt, getdate

from inventory_tools.tests.setup import (
	GENERIC_MR_DUPLICATE_PO,
	GENERIC_MR_PARCHMENT,
	GENERIC_MR_QTY_MISMATCH,
	GENERIC_MR_SETTING_OFF,
	SALT_MR_REORDER,
	fixture_material_request,
)

COMPANY = "Ambrosia Pie Company"


def configure_po_from_mr(po, supplier="Freedom Provisions"):
	po.supplier = supplier
	po.buying_price_list = "Bakery Buying"
	po.schedule_date = getdate()
	for row in po.items:
		row.schedule_date = getdate()


def replace_item(row, item_code, qty=1, rate=34):
	item = frappe.get_cached_doc("Item", item_code)
	row.item_code = item_code
	row.item_name = item.item_name
	row.item_group = item.item_group
	row.uom = item.stock_uom
	row.stock_uom = item.stock_uom
	row.conversion_factor = 1
	row.qty = qty
	row.rate = rate


def generic_item_field_hidden():
	return bool(
		frappe.db.exists(
			"Property Setter",
			{"doc_type": "Item", "field_name": "is_generic_item", "property": "hidden", "value": "1"},
		)
	)


@pytest.mark.order(150)
def test_stock_item_cannot_be_generic():
	item = frappe.get_doc("Item", "Salt")
	item.is_generic_item = 1
	with pytest.raises(frappe.ValidationError):
		item.save()


@pytest.mark.order(152)
def test_replacing_generic_item_resolves_material_request_line():
	"""
	A buyer replaces a generic placeholder on the Purchase Order with Salt. Submit rewrites the
	fixtured Material Request line to the purchased item and records the placeholder.
	"""
	mr = fixture_material_request(GENERIC_MR_PARCHMENT)
	mri_name = mr.items[0].name

	po = make_purchase_order(mr.name)
	configure_po_from_mr(po)
	replace_item(po.items[0], "Salt")
	po.save()
	po.submit()

	mri = frappe.get_doc("Material Request Item", mri_name)
	assert mri.item_code == "Salt"
	assert mri.generic_item_code == "Miscellaneous Supplies"
	assert mri.uom == frappe.get_cached_value("Item", "Salt", "stock_uom")
	assert flt(mri.ordered_qty) == flt(mri.stock_qty)
	assert flt(frappe.db.get_value("Material Request", mr.name, "per_ordered")) == 100

	po.cancel()
	mri.reload()
	assert mri.item_code == "Salt"
	assert flt(mri.ordered_qty) == 0
	assert flt(frappe.db.get_value("Material Request", mr.name, "per_ordered")) == 0


@pytest.mark.order(154)
def test_generic_line_replaced_by_one_po_line_only():
	"""Two Purchase Order lines cannot both replace the same generic Material Request line."""
	mr = fixture_material_request(GENERIC_MR_DUPLICATE_PO)
	mri_name = mr.items[0].name
	existing_pos = set(frappe.get_all("Purchase Order", pluck="name"))

	po = make_purchase_order(mr.name)
	configure_po_from_mr(po)
	replace_item(po.items[0], "Salt")
	po.append("items", po.items[0].as_dict(no_default_fields=True))
	replace_item(po.items[1], "Sugar")
	with pytest.raises(frappe.ValidationError, match="only be replaced by one"):
		po.save()

	mri = frappe.db.get_value(
		"Material Request Item",
		mri_name,
		["item_code", "generic_item_code"],
		as_dict=True,
	)
	assert mri.item_code == "Miscellaneous Supplies"
	assert not mri.generic_item_code
	assert set(frappe.get_all("Purchase Order", pluck="name")) == existing_pos


@pytest.mark.order(156)
def test_non_generic_mr_requires_matching_item():
	"""Swapping Salt for Sugar on a normal Purchase Material Request is rejected with no new PO."""
	mr = fixture_material_request(SALT_MR_REORDER)
	existing_pos = set(frappe.get_all("Purchase Order", pluck="name"))

	po = make_purchase_order(mr.name)
	configure_po_from_mr(po)
	replace_item(po.items[0], "Sugar")
	with pytest.raises(frappe.ValidationError, match="Item Code"):
		po.save()

	assert set(frappe.get_all("Purchase Order", pluck="name")) == existing_pos


@pytest.mark.order(158)
def test_generic_qty_mismatch_policy():
	"""Error policy blocks save; Warn allows submit and copies the Purchase Order quantity onto the request."""
	mr = fixture_material_request(GENERIC_MR_QTY_MISMATCH)
	mri_name = mr.items[0].name

	po = make_purchase_order(mr.name)
	configure_po_from_mr(po)
	replace_item(po.items[0], "Salt", qty=12)

	settings = frappe.get_doc("Inventory Tools Settings", COMPANY)
	settings.generic_item_qty_mismatch = "Error"
	settings.save()
	try:
		with pytest.raises(frappe.ValidationError, match="differs from"):
			po.save()
	finally:
		settings.generic_item_qty_mismatch = "Warn"
		settings.save()

	po.save()
	po.submit()
	mri = frappe.get_doc("Material Request Item", mri_name)
	assert flt(mri.qty) == 12
	assert flt(frappe.db.get_value("Material Request", mr.name, "per_ordered")) == 100


@pytest.mark.order(160)
def test_generic_swap_blocked_and_field_hidden_when_setting_disabled():
	settings = frappe.get_doc("Inventory Tools Settings", COMPANY)
	assert not generic_item_field_hidden()
	settings.enable_generic_items = 0
	settings.save()
	try:
		assert generic_item_field_hidden()
		mr = fixture_material_request(GENERIC_MR_SETTING_OFF)
		existing_pos = set(frappe.get_all("Purchase Order", pluck="name"))
		po = make_purchase_order(mr.name)
		configure_po_from_mr(po)
		replace_item(po.items[0], "Salt")
		with pytest.raises(frappe.ValidationError, match="Item Code"):
			po.save()
		assert set(frappe.get_all("Purchase Order", pluck="name")) == existing_pos
	finally:
		settings.enable_generic_items = 1
		settings.save()
	assert not generic_item_field_hidden()


@pytest.mark.order(162)
def test_generic_item_purchase_order_saves_without_price_but_cannot_submit():
	"""
	A draft Purchase Order may carry the generic placeholder without creating an Item Price,
	but it cannot be submitted until the buyer replaces the item.
	"""
	mr = fixture_material_request(GENERIC_MR_SETTING_OFF)
	stock_settings = frappe.get_single("Stock Settings")
	stock_settings.auto_insert_price_list_rate_if_missing = 1
	stock_settings.save()
	try:
		po = make_purchase_order(mr.name)
		configure_po_from_mr(po)
		po.items[0].rate = 34
		po.save()
		assert not frappe.db.exists("Item Price", {"item_code": "Miscellaneous Supplies"})

		with pytest.raises(frappe.ValidationError, match="Replace generic placeholder"):
			po.submit()
		assert frappe.db.get_value("Purchase Order", po.name, "docstatus") == 0
		assert not flt(frappe.db.get_value("Material Request Item", mr.items[0].name, "ordered_qty"))
	finally:
		stock_settings.auto_insert_price_list_rate_if_missing = 0
		stock_settings.save()


@pytest.mark.order(164)
def test_item_price_validate_rejects_generic_item():
	price = frappe.get_doc(
		{
			"doctype": "Item Price",
			"item_code": "Miscellaneous Supplies",
			"price_list": "Bakery Buying",
			"price_list_rate": 34,
		}
	)
	with pytest.raises(frappe.ValidationError, match="generic placeholder"):
		price.insert()


@pytest.mark.order(166)
def test_material_request_keeps_generic_rate_without_price_alert():
	"""
	Saving a Material Request with only a generic line keeps the requester's rate and does not
	announce a price-list rate update, on insert or when the buying price list changes.
	"""
	frappe.local.message_log = []
	mr = frappe.new_doc("Material Request")
	mr.company = COMPANY
	mr.material_request_type = "Purchase"
	mr.transaction_date = getdate()
	mr.schedule_date = getdate()
	mr.buying_price_list = "Standard Buying"
	mr.append(
		"items",
		{
			"item_code": "Miscellaneous Supplies",
			"qty": 1,
			"rate": 333.23,
			"warehouse": "Storeroom - APC",
			"uom": "Unit",
			"description": "Replacement bench scraper.",
		},
	)
	mr.save()
	assert not [m for m in frappe.local.message_log if "Item rates" in str(m)]

	mr.buying_price_list = "Bakery Buying"
	mr.save()
	assert not [m for m in frappe.local.message_log if "Item rates" in str(m)]
	assert flt(frappe.db.get_value("Material Request Item", mr.items[0].name, "rate")) == 333.23


@pytest.mark.order(168)
def test_purchase_receipt_rejects_generic_item():
	"""A hand-entered Purchase Receipt cannot receive the generic placeholder."""
	existing_prs = set(frappe.get_all("Purchase Receipt", pluck="name"))
	pr = frappe.new_doc("Purchase Receipt")
	pr.company = COMPANY
	pr.supplier = "Freedom Provisions"
	pr.posting_date = getdate()
	pr.append(
		"items",
		{
			"item_code": "Miscellaneous Supplies",
			"qty": 1,
			"rate": 34,
			"uom": "Unit",
			"warehouse": "Storeroom - APC",
		},
	)
	with pytest.raises(frappe.ValidationError, match="Replace generic placeholder"):
		pr.save()
	assert set(frappe.get_all("Purchase Receipt", pluck="name")) == existing_prs
