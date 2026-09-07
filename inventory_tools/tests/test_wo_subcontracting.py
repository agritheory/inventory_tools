# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from erpnext.buying.doctype.purchase_order.purchase_order import (
	make_purchase_invoice as make_pi_from_po,
)
from frappe.utils import getdate

from inventory_tools.inventory_tools.overrides.purchase_invoice import get_stock_entries
from inventory_tools.inventory_tools.overrides.work_order import (
	add_to_existing_purchase_order,
	in_existing_po,
	make_subcontracted_purchase_order,
	make_stock_entry,
)

COMPANY = "Ambrosia Pie Company"
SUPPLIER = "Credible Contract Baking"
ITEM = "Pie Crust"
WIP_WAREHOUSE = "Credible Contract Baking - APC"
RETURN_WAREHOUSE = "Refrigerated Display - APC"


def get_subcontracted_wo():
	return frappe.db.get_value(
		"Work Order",
		{
			"production_item": ITEM,
			"company": COMPANY,
			"supplier": SUPPLIER,
			"docstatus": 1,
		},
		"name",
		order_by="creation asc",
	)


@pytest.mark.order(28)
def test_subcontracted_po_created_from_wo():
	"""Fixture creates a submitted subcontracted PO linked to the subcontracted Work Order."""
	wo_name = get_subcontracted_wo()
	assert wo_name, f"No submitted subcontracted Work Order for {ITEM} (supplier={SUPPLIER}) found"

	po_names = in_existing_po(wo_name)
	assert po_names, f"No Purchase Order found linked to Work Order {wo_name}"

	po = frappe.get_doc("Purchase Order", po_names[0])
	assert po.is_subcontracted == 1
	assert po.supplier == SUPPLIER
	assert po.supplier_warehouse == WIP_WAREHOUSE

	pie_crust_items = [i for i in po.items if i.item_code == ITEM]
	assert pie_crust_items, f"No {ITEM} item row found in PO {po.name}"

	wo_refs = [row.work_order for row in po.subcontracting]
	assert wo_name in wo_refs, f"Work Order {wo_name} not referenced in PO subcontracting table"


@pytest.mark.order(29)
def test_subcontracted_po_add_to_existing():
	"""add_to_existing_purchase_order adds a second WO to a draft PO without duplicating."""
	wo_name = get_subcontracted_wo()
	po_names = in_existing_po(wo_name)
	assert po_names

	po_name = po_names[0]
	po = frappe.get_doc("Purchase Order", po_name)
	original_qty = sum(i.qty for i in po.items if i.item_code == ITEM)
	original_wo_count = len(po.subcontracting)

	# Calling add_to_existing on a WO already in the PO should warn but not duplicate
	add_to_existing_purchase_order(wo_name, po_name)

	po.reload()
	new_wo_count = len(po.subcontracting)
	assert new_wo_count == original_wo_count, "WO should not be added twice to the same PO"
	assert sum(i.qty for i in po.items if i.item_code == ITEM) == original_qty


@pytest.mark.order(30)
def test_material_transfer_routes_to_subcontractor_warehouse():
	"""Material Transfer for Manufacture sets t_warehouse to the subcontractor's WIP warehouse."""
	wo_name = get_subcontracted_wo()
	assert wo_name

	se_dict = make_stock_entry(wo_name, "Material Transfer for Manufacture")
	se = frappe.get_doc(**se_dict)

	for row in se.items:
		assert (
			row.t_warehouse == WIP_WAREHOUSE
		), f"Item {row.item_code}: expected t_warehouse={WIP_WAREHOUSE}, got {row.t_warehouse}"


@pytest.mark.order(31)
def test_manufacture_se_routes_correctly_and_submits():
	"""Manufacture SE consumes from WIP warehouse and receives finished goods into return warehouse."""
	wo_name = get_subcontracted_wo()
	assert wo_name
	wo = frappe.get_doc("Work Order", wo_name)

	se_dict = make_stock_entry(wo_name, "Manufacture")
	se = frappe.get_doc(**se_dict)

	for row in se.items:
		if row.is_finished_item:
			assert (
				row.t_warehouse == RETURN_WAREHOUSE
			), f"Finished item {row.item_code}: expected t_warehouse={RETURN_WAREHOUSE}, got {row.t_warehouse}"
			assert (
				not row.s_warehouse
			), f"Finished item {row.item_code}: s_warehouse should be empty, got {row.s_warehouse}"
		else:
			assert (
				row.s_warehouse == WIP_WAREHOUSE
			), f"Raw material {row.item_code}: expected s_warehouse={WIP_WAREHOUSE}, got {row.s_warehouse}"
			assert (
				not row.t_warehouse
			), f"Raw material {row.item_code}: t_warehouse should be empty, got {row.t_warehouse}"

	# Seed stock into WIP warehouse so the SE can be submitted.
	# Post the receipt earlier the same day so SLE rebuild sees it before Manufacture.
	material_receipt = frappe.copy_doc(se)
	material_receipt.stock_entry_type = "Material Receipt"
	material_receipt.work_order = None
	material_receipt.fg_completed_qty = 0
	material_receipt.set_posting_time = 1
	material_receipt.posting_date = se.posting_date
	material_receipt.posting_time = "00:00:01"
	finished_rows = [row for row in material_receipt.items if row.is_finished_item]
	for row in finished_rows:
		material_receipt.remove(row)
	for row in material_receipt.items:
		row.t_warehouse = row.s_warehouse
		row.s_warehouse = None
		row.expense_account = "5119 - Stock Adjustment - APC"
		price_list_rate = frappe.db.get_value(
			"Item Price",
			{"item_code": row.item_code, "price_list": "Bakery Buying", "buying": 1},
			"price_list_rate",
		)
		if price_list_rate:
			row.basic_rate = price_list_rate
	material_receipt.save()
	material_receipt.submit()

	se.set_posting_time = 1
	se.posting_time = "12:00:00"
	se.save()
	se.submit()

	se.reload()
	finished_rows = [r for r in se.items if r.is_finished_item]
	assert finished_rows, "No finished item row found in submitted Manufacture SE"
	assert se.fg_completed_qty == wo.qty


@pytest.mark.order(32)
def test_get_stock_entries_for_pi_reconciliation():
	"""get_stock_entries returns the submitted Manufacture SE for the subcontracted WO."""
	wo_name = get_subcontracted_wo()
	po_names = in_existing_po(wo_name)
	assert po_names

	results = get_stock_entries(po_names)
	assert results, "get_stock_entries returned no results"

	item_codes = [r.item_code for r in results]
	assert ITEM in item_codes, f"{ITEM} not found in get_stock_entries results"

	for row in results:
		if row.item_code == ITEM:
			assert row.paid_qty == 0, f"paid_qty should be 0 before any PI, got {row.paid_qty}"
			assert row.qty > 0, "qty should be positive"


@pytest.mark.order(33)
def test_purchase_invoice_paid_qty_tracking():
	"""Submitting a subcontracted PI updates paid_qty on the Stock Entry Detail."""
	wo_name = get_subcontracted_wo()
	po_names = in_existing_po(wo_name)
	assert po_names
	po = frappe.get_doc("Purchase Order", po_names[0])

	se_rows = get_stock_entries(po_names)
	assert se_rows, "No stock entries available for PI reconciliation"

	# Take the first finished-good row to invoice
	se_row = next(r for r in se_rows if r.item_code == ITEM)
	total_qty = se_row.qty
	to_pay_qty = total_qty / 2  # Pay for half now

	# Build PI from PO so rates, accounts and PO references are populated correctly
	pi = frappe.get_doc(make_pi_from_po(po.name))
	pi.is_subcontracted = 1
	pi.supplier_warehouse = RETURN_WAREHOUSE
	pi.bill_no = f"TEST-SUBC-{frappe.generate_hash(length=6)}"
	pi.bill_date = getdate()

	# Adjust to partial qty
	for item in pi.items:
		item.qty = to_pay_qty
		item.stock_qty = to_pay_qty

	# Populate subcontracting table
	pi.append(
		"subcontracting",
		{
			"work_order": se_row.work_order,
			"stock_entry": se_row.stock_entry,
			"se_detail_name": se_row.se_detail_name,
			"purchase_order": se_row.purchase_order,
			"item_code": se_row.item_code,
			"item_name": se_row.item_name,
			"qty": se_row.qty,
			"transfer_qty": se_row.transfer_qty,
			"uom": se_row.uom,
			"stock_uom": se_row.stock_uom,
			"conversion_factor": se_row.conversion_factor,
			"valuation_rate": se_row.valuation_rate,
			"paid_qty": se_row.paid_qty,
			"to_pay_qty": to_pay_qty,
		},
	)

	pi.save()
	pi.submit()

	# Verify paid_qty was updated on the Stock Entry Detail
	updated_paid_qty = frappe.db.get_value("Stock Entry Detail", se_row.se_detail_name, "paid_qty")
	assert (
		updated_paid_qty == to_pay_qty
	), f"Expected paid_qty={to_pay_qty} on SE Detail, got {updated_paid_qty}"

	# Verify remaining qty shows correctly in a fresh get_stock_entries call
	remaining_rows = get_stock_entries(po_names)
	remaining_row = next((r for r in remaining_rows if r.item_code == ITEM), None)
	assert remaining_row is not None, f"{ITEM} should still appear with outstanding qty"
	assert remaining_row.paid_qty == to_pay_qty
	assert remaining_row.qty - remaining_row.paid_qty == total_qty - to_pay_qty
