# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import flt, getdate

from inventory_tools.inventory_tools.report.material_demand.material_demand import (
	execute as execute_material_demand,
)
from inventory_tools.tests.setup import create_southern_fruit_purchase_orders

# Setup runs Bayberry-only PO -> PR (quarantine) -> QI (release) before these tests; Bayberry satisfied.


def assert_setup_bayberry_po_exists():
	"""Verify setup created submitted PO for Bayberry (Southern Fruit Supply)."""
	po_items = frappe.get_all(
		"Purchase Order Item",
		filters={"item_code": "Bayberry"},
		fields=["parent"],
	)
	po_names = {p["parent"] for p in po_items}
	for name in po_names:
		po = frappe.get_doc("Purchase Order", name)
		if po.supplier == "Southern Fruit Supply" and po.docstatus == 1:
			return
	assert False, "Setup should create submitted PO for Bayberry from Southern Fruit Supply"


@pytest.mark.order(17)
def test_report_po_without_aggregation():
	assert_setup_bayberry_po_exists()
	filters = frappe._dict(
		{"end_date": getdate(), "price_list": "Bakery Wholesale", "company": "Ambrosia Pie Company"}
	)
	columns, rows = execute_material_demand(filters)
	assert len(rows) == 34
	assert rows[1].get("supplier") == "Chelsea Fruit Co"

	selected_rows = [
		row
		for row in rows
		if row.get("supplier") not in ["Southern Fruit Supply", "Unity Bakery Supply"]
	]

	frappe.call(
		"inventory_tools.inventory_tools.report.material_demand.material_demand.create",
		**{
			"company": "Ambrosia Pie Company",
			"email_template": "",
			"filters": filters,
			"creation_type": "po",
			"rows": frappe.as_json(selected_rows),
		},
	)

	pos = frappe.get_all(
		"Purchase Order",
		{"supplier": ["!=", "Southern Fruit Supply"]},
		["name", "supplier", "grand_total"],
	)
	assert "Unity Bakery Supply" not in [p.get("supplier") for p in pos]
	for po in pos:
		if po.supplier == "Chelsea Fruit Co":
			assert po.grand_total == flt(501.07, 2)
		elif po.supplier == "Freedom Provisions":
			assert po.grand_total == flt(375.89, 2)
		elif po.supplier == "Credible Contract Baking":
			continue  # subcontracting PO created by fixture, not this test
		else:
			raise AssertionError(f"{po.supplier} should not be in this test")
		frappe.delete_doc("Purchase Order", po.name)


@pytest.mark.order(18)
def test_report_rfq_without_aggregation():
	filters = frappe._dict(
		{"end_date": getdate(), "price_list": "Bakery Wholesale", "company": "Ambrosia Pie Company"}
	)
	columns, rows = execute_material_demand(filters)
	assert len(rows) == 34
	assert rows[1].get("supplier") == "Chelsea Fruit Co"

	selected_rows = [row for row in rows if row.get("supplier") not in ["Southern Fruit Supply"]]

	frappe.call(
		"inventory_tools.inventory_tools.report.material_demand.material_demand.create",
		**{
			"company": "Ambrosia Pie Company",
			"email_template": "Dispatch Notification",
			"filters": filters,
			"creation_type": "rfq",
			"rows": frappe.as_json(selected_rows),
		},
	)

	rfqs = [
		frappe.get_doc("Request for Quotation", r) for r in frappe.get_all("Request for Quotation")
	]
	for rfq in rfqs:
		if len(rfq.suppliers) == 1 and [r.supplier for r in rfq.suppliers] == ["Chelsea Fruit Co"]:
			assert len(rfq.items) == 9
			# Bayberry, Cloudberry, Cocoplum, Damson Plum, Gooseberry, Hairless Rambutan, Kaduka Lime, Limequat, Tayberry
		elif len(rfq.suppliers) == 1 and [r.supplier for r in rfq.suppliers] == ["Freedom Provisions"]:
			assert len(rfq.items) == 4  # Cornstarch, Flour, Salt, Sugar
		elif len(rfq.suppliers) == 2 and [r.supplier for r in rfq.suppliers] == [
			"Chelsea Fruit Co",
			"Freedom Provisions",
		]:
			assert len(rfq.items) == 1  # Butter
		elif len(rfq.suppliers) == 2 and [r.supplier for r in rfq.suppliers] == [
			"Freedom Provisions",
			"Unity Bakery Supply",
		]:
			assert len(rfq.items) == 3  # Parchment Paper, Pie Box, Pie Tin
		else:
			raise AssertionError("RFQs items have not combined correctly")
		rfq.delete()


@pytest.mark.order(19)
def test_report_item_based_without_aggregation():
	filters = frappe._dict(
		{"end_date": getdate(), "price_list": "Bakery Wholesale", "company": "Ambrosia Pie Company"}
	)
	columns, rows = execute_material_demand(filters)
	assert len(rows) == 34

	selected_rows = [
		row
		for row in rows
		if row.get("supplier") not in ["Southern Fruit Supply", "Unity Bakery Supply"]
	]

	frappe.call(
		"inventory_tools.inventory_tools.report.material_demand.material_demand.create",
		**{
			"company": "Ambrosia Pie Company",
			"email_template": "Dispatch Notification",
			"filters": filters,
			"creation_type": "item_based",
			"rows": frappe.as_json(selected_rows),
		},
	)

	pos = frappe.get_all("Purchase Order", ["name", "supplier", "grand_total"])
	assert "Unity Bakery Supply" not in [p.get("supplier") for p in pos]
	for po in pos:
		if po.supplier == "Chelsea Fruit Co":
			assert po.grand_total == flt(501.07, 2)
		elif po.supplier == "Freedom Provisions":
			assert po.grand_total == flt(375.89, 2)
		elif po.supplier in ("Southern Fruit Supply", "Credible Contract Baking"):
			continue  # Southern Fruit Supply excluded by design; Credible Contract Baking is the subcontracting fixture PO
		else:
			raise AssertionError(f"{po.supplier} should not be in this test")
		frappe.delete_doc("Purchase Order", po.name)

	rfqs = [
		frappe.get_doc("Request for Quotation", r) for r in frappe.get_all("Request for Quotation")
	]
	for rfq in rfqs:
		if len(rfq.suppliers) == 1 and [r.supplier for r in rfq.suppliers] == ["Chelsea Fruit Co"]:
			assert len(rfq.items) == 1
		rfq.delete()


@pytest.mark.order(20)
def test_report_po_with_aggregation_and_no_aggregation_warehouse():
	"""
	Test PO creation with aggregation enabled but no aggregation warehouse set.
	This creates POs for Southern Fruit Supply and Freedom Provisions across companies.
	Warehouse should match the original Material Request warehouse (no override).
	"""
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.purchase_order_aggregation_company = settings.name
	settings.aggregated_purchasing_warehouse = None
	settings.update_warehouse_path = True
	settings.save()

	existing_pos = set(frappe.get_all("Purchase Order", pluck="name"))

	filters = frappe._dict({"end_date": getdate(), "price_list": "Bakery Wholesale"})
	columns, rows = execute_material_demand(filters)
	assert len(rows) == 48
	assert rows[1].get("supplier") == "Chelsea Fruit Co"

	selected_rows = [
		row for row in rows if row.get("supplier") not in ["Chelsea Fruit Co", "Unity Bakery Supply"]
	]

	frappe.call(
		"inventory_tools.inventory_tools.report.material_demand.material_demand.create",
		**{
			"company": "Chelsea Fruit Co",
			"email_template": "",
			"filters": filters,
			"creation_type": "po",
			"rows": frappe.as_json(selected_rows),
		},
	)

	all_pos = set(frappe.get_all("Purchase Order", pluck="name"))
	new_po_names = all_pos - existing_pos

	new_pos = [frappe.get_doc("Purchase Order", name) for name in new_po_names]
	assert "Unity Bakery Supply" not in [p.supplier for p in new_pos]

	for po in new_pos:
		if po.supplier == "Southern Fruit Supply":
			for item in po.items:
				mr_wh = frappe.get_value("Material Request Item", item.material_request_item, "warehouse")
				assert item.warehouse == mr_wh, f"Warehouse mismatch: {item.warehouse} != {mr_wh}"
				mr_company = frappe.get_value("Material Request", item.material_request, "company")
				assert item.company == mr_company, f"Company mismatch: {item.company} != {mr_company}"
		elif po.supplier == "Freedom Provisions":
			for item in po.items:
				mr_wh = frappe.get_value("Material Request Item", item.material_request_item, "warehouse")
				assert item.warehouse == mr_wh, f"Warehouse mismatch: {item.warehouse} != {mr_wh}"
				mr_company = frappe.get_value("Material Request", item.material_request, "company")
				assert item.company == mr_company, f"Company mismatch: {item.company} != {mr_company}"
		else:
			raise AssertionError(f"Unexpected supplier {po.supplier} in new POs")
		frappe.delete_doc("Purchase Order", po.name)


@pytest.mark.order(21)
def test_report_po_with_aggregation_and_aggregation_warehouse():
	"""
	Test PO creation with aggregation enabled AND aggregation warehouse set.
	This creates POs for Southern Fruit Supply and Freedom Provisions.
	Warehouse should be overridden to the aggregation company's warehouse.
	"""
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.purchase_order_aggregation_company = settings.name
	settings.aggregated_purchasing_warehouse = "Stores - CFC"
	settings.update_warehouse_path = True
	settings.save()

	existing_pos = set(frappe.get_all("Purchase Order", pluck="name"))

	filters = frappe._dict({"end_date": getdate(), "price_list": "Bakery Wholesale"})
	columns, rows = execute_material_demand(filters)
	assert len(rows) == 48
	assert rows[1].get("supplier") == "Chelsea Fruit Co"

	selected_rows = [
		row for row in rows if row.get("supplier") not in ["Chelsea Fruit Co", "Unity Bakery Supply"]
	]

	frappe.call(
		"inventory_tools.inventory_tools.report.material_demand.material_demand.create",
		**{
			"company": "Chelsea Fruit Co",
			"email_template": "",
			"filters": filters,
			"creation_type": "po",
			"rows": frappe.as_json(selected_rows),
		},
	)

	all_pos = set(frappe.get_all("Purchase Order", pluck="name"))
	new_po_names = all_pos - existing_pos

	new_pos = [frappe.get_doc("Purchase Order", name) for name in new_po_names]
	assert "Unity Bakery Supply" not in [p.supplier for p in new_pos]

	for po in new_pos:
		if po.supplier == "Southern Fruit Supply":
			for item in po.items:
				wh_company = frappe.get_value("Warehouse", item.warehouse, "company")
				assert wh_company == po.company, f"Warehouse company mismatch: {wh_company} != {po.company}"
				mr_company = frappe.get_value("Material Request", item.material_request, "company")
				assert item.company == mr_company, f"Company mismatch: {item.company} != {mr_company}"
		elif po.supplier == "Freedom Provisions":
			for item in po.items:
				wh_company = frappe.get_value("Warehouse", item.warehouse, "company")
				assert wh_company == po.company, f"Warehouse company mismatch: {wh_company} != {po.company}"
				mr_company = frappe.get_value("Material Request", item.material_request, "company")
				assert item.company == mr_company, f"Company mismatch: {item.company} != {mr_company}"
		else:
			raise AssertionError(f"Unexpected supplier {po.supplier} in new POs")
		frappe.delete_doc("Purchase Order", po.name)


@pytest.mark.order(34)
def test_multi_company_make_purchase_receipts_match_warehouse_company():
	"""Create Purchase Receipts dialog splits lines by requesting company."""
	from inventory_tools.inventory_tools.overrides.purchase_order import make_purchase_receipts

	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.purchase_order_aggregation_company = settings.name
	settings.aggregated_purchasing_warehouse = None
	settings.update_warehouse_path = True
	settings.save()

	existing_pos = set(frappe.get_all("Purchase Order", pluck="name"))
	filters = frappe._dict({"end_date": getdate(), "price_list": "Bakery Wholesale"})
	columns, rows = execute_material_demand(filters)
	selected_rows = [
		row for row in rows if row.get("supplier") == "Southern Fruit Supply" and row.get("item_code")
	][:4]
	assert len(selected_rows) >= 2

	frappe.call(
		"inventory_tools.inventory_tools.report.material_demand.material_demand.create",
		**{
			"company": "Chelsea Fruit Co",
			"email_template": "",
			"filters": filters,
			"creation_type": "po",
			"rows": frappe.as_json(selected_rows),
		},
	)

	po_name = next(iter(set(frappe.get_all("Purchase Order", pluck="name")) - existing_pos))
	po = frappe.get_doc("Purchase Order", po_name)
	assert po.multi_company_purchase_order
	po.submit()

	pr_names = make_purchase_receipts(po.name, [item.name for item in po.items])
	assert len(pr_names) >= 1
	for pr_name in pr_names:
		pr = frappe.get_doc("Purchase Receipt", pr_name)
		settings = frappe.get_doc("Inventory Tools Settings", pr.company)
		expected_putaway = settings.apply_putaway_rule_on_multi_company_receipt
		assert pr.apply_putaway_rule == expected_putaway
		for item in pr.items:
			warehouse_company = frappe.get_value("Warehouse", item.warehouse, "company")
			assert (
				warehouse_company == pr.company
			), f"{item.warehouse} belongs to {warehouse_company}, not {pr.company}"

	for pr_name in pr_names:
		frappe.delete_doc("Purchase Receipt", pr_name, force=1)
	po.reload()
	po.cancel()
	frappe.delete_doc("Purchase Order", po.name, force=1)


@pytest.mark.order(35)
def test_seed_southern_fruit_po_prs_from_material_demand():
	"""After material demand PO tests, seed submitted PO+PR pairs for Southern Fruit Supply."""
	result = create_southern_fruit_purchase_orders(
		supplier="Southern Fruit Supply",
		create_draft_prs=True,
		submit_prs=True,
		enable_quarantine=False,
		force=True,
	)
	summary = {
		"selected_row_count": result.get("selected_row_count", 0),
		"created_po_count": len(result.get("purchase_orders", [])),
		"submitted_pairs": [
			{
				"po": entry["purchase_order"],
				"pr": entry.get("purchase_receipt"),
				"prs": entry.get("purchase_receipts") or [],
				"items": entry["items"],
				"pr_docstatus": entry.get("pr_docstatus"),
			}
			for entry in result.get("purchase_orders", [])
		],
		"errors": result.get("errors", []),
	}

	assert summary["selected_row_count"] > 0
	assert summary["submitted_pairs"], summary["errors"]
	assert not summary["errors"]

	item_codes = {item_code for pair in summary["submitted_pairs"] for item_code in pair["items"]}
	assert len(item_codes) >= 5

	all_pr_names = []
	for pair in summary["submitted_pairs"]:
		all_pr_names.extend(pair.get("prs") or ([pair["pr"]] if pair.get("pr") else []))
	assert len(all_pr_names) >= 2

	for pr_name in all_pr_names:
		pr = frappe.get_doc("Purchase Receipt", pr_name)
		assert pr.docstatus == 1
		assert pr.items
		for item in pr.items:
			warehouse_company = frappe.get_value("Warehouse", item.warehouse, "company")
			assert (
				warehouse_company == pr.company
			), f"{item.warehouse} belongs to {warehouse_company}, not {pr.company}"
