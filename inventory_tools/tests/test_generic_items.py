# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from frappe.utils import flt, getdate


def make_generic_material_request(qty=1, rate=34):
	mr = frappe.new_doc("Material Request")
	mr.company = "Ambrosia Pie Company"
	mr.material_request_type = "Purchase"
	mr.transaction_date = getdate()
	mr.schedule_date = getdate()
	mr.append(
		"items",
		{
			"item_code": "Miscellaneous Supplies",
			"qty": qty,
			"rate": rate,
			"warehouse": "Storeroom - APC",
			"uom": "Unit",
		},
	)
	mr.submit()
	return mr


def configure_po_from_mr(po, supplier="Freedom Provisions"):
	po.supplier = supplier
	po.buying_price_list = "Bakery Buying"
	po.schedule_date = getdate()
	for row in po.items:
		row.schedule_date = getdate()


@pytest.mark.order(142)
def test_stock_item_cannot_be_generic():
	item = frappe.get_doc("Item", "Salt")
	item.is_generic_item = 1
	with pytest.raises(frappe.ValidationError):
		item.save()


@pytest.mark.order(143)
def test_generic_mr_allows_different_po_item():
	mr = make_generic_material_request()
	po = make_purchase_order(mr.name)
	configure_po_from_mr(po)
	po.items[0].item_code = "Salt"
	po.items[0].rate = 34
	po.items[0].qty = 1
	po.save()
	po.submit()

	mri = frappe.get_doc("Material Request Item", mr.items[0].name)
	assert flt(mri.per_ordered, 2) == 100

	po.cancel()
	frappe.delete_doc("Purchase Order", po.name, force=1)
	mr.cancel()
	frappe.delete_doc("Material Request", mr.name, force=1)


@pytest.mark.order(144)
def test_generic_mr_split_across_po_rows_tracks_amount():
	mr = make_generic_material_request(qty=1, rate=100)
	po = make_purchase_order(mr.name)
	configure_po_from_mr(po)
	mri_name = po.items[0].material_request_item
	mr_name = po.items[0].material_request

	po.items[0].item_code = "Salt"
	po.items[0].qty = 1
	po.items[0].rate = 40
	template = po.items[0].as_dict()
	po.append(
		"items",
		{
			"item_code": "Sugar",
			"qty": 1,
			"rate": 30,
			"warehouse": template.warehouse,
			"uom": template.uom,
			"material_request": mr_name,
			"material_request_item": mri_name,
			"schedule_date": getdate(),
		},
	)
	po.save()
	po.submit()

	mri = frappe.get_doc("Material Request Item", mr.items[0].name)
	assert flt(mri.per_ordered, 2) == 70

	po.cancel()
	frappe.delete_doc("Purchase Order", po.name, force=1)
	mr.cancel()
	frappe.delete_doc("Material Request", mr.name, force=1)


@pytest.mark.order(145)
def test_non_generic_mr_requires_matching_item():
	mr = frappe.new_doc("Material Request")
	mr.company = "Ambrosia Pie Company"
	mr.material_request_type = "Purchase"
	mr.transaction_date = getdate()
	mr.schedule_date = getdate()
	mr.append(
		"items",
		{
			"item_code": "Salt",
			"qty": 1,
			"warehouse": "Storeroom - APC",
			"uom": "Pound",
		},
	)
	mr.submit()

	po = make_purchase_order(mr.name)
	configure_po_from_mr(po)
	po.items[0].item_code = "Sugar"
	with pytest.raises(frappe.ValidationError, match="Item Code"):
		po.save()

	frappe.delete_doc("Purchase Order", po.name, force=1)
	mr.cancel()
	frappe.delete_doc("Material Request", mr.name, force=1)


@pytest.mark.order(146)
def test_generic_swap_blocked_when_setting_disabled():
	frappe.set_value("Inventory Tools Settings", "Ambrosia Pie Company", "enable_generic_items", 0)
	try:
		mr = make_generic_material_request()
		po = make_purchase_order(mr.name)
		configure_po_from_mr(po)
		po.items[0].item_code = "Salt"
		with pytest.raises(frappe.ValidationError, match="Item Code"):
			po.save()
		frappe.delete_doc("Purchase Order", po.name, force=1)
		mr.cancel()
		frappe.delete_doc("Material Request", mr.name, force=1)
	finally:
		frappe.set_value("Inventory Tools Settings", "Ambrosia Pie Company", "enable_generic_items", 1)
