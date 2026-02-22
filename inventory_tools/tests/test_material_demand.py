# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import flt, getdate

from inventory_tools.inventory_tools.report.material_demand.material_demand import (
	execute as execute_material_demand,
)

# Setup runs Bayberry-only PO -> PR (quarantine) -> QI (release) before these tests; Bayberry satisfied.


def _assert_setup_bayberry_po_exists():
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
	_assert_setup_bayberry_po_exists()
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
		elif po.supplier == "Southern Fruit Supply":
			continue
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

	# Capture existing POs before test creates new ones
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

	# Only check POs created by THIS test
	all_pos = set(frappe.get_all("Purchase Order", pluck="name"))
	new_po_names = all_pos - existing_pos

	new_pos = [frappe.get_doc("Purchase Order", name) for name in new_po_names]
	assert "Unity Bakery Supply" not in [p.supplier for p in new_pos]

	for po in new_pos:
		if po.supplier == "Southern Fruit Supply":
			# Verify warehouse matches MR warehouse (no aggregation override)
			for item in po.items:
				mr_wh = frappe.get_value("Material Request Item", item.material_request_item, "warehouse")
				assert item.warehouse == mr_wh, f"Warehouse mismatch: {item.warehouse} != {mr_wh}"
		elif po.supplier == "Freedom Provisions":
			for item in po.items:
				mr_wh = frappe.get_value("Material Request Item", item.material_request_item, "warehouse")
				assert item.warehouse == mr_wh, f"Warehouse mismatch: {item.warehouse} != {mr_wh}"
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

	# Capture existing POs before test creates new ones
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

	# Only check POs created by THIS test
	all_pos = set(frappe.get_all("Purchase Order", pluck="name"))
	new_po_names = all_pos - existing_pos

	new_pos = [frappe.get_doc("Purchase Order", name) for name in new_po_names]
	assert "Unity Bakery Supply" not in [p.supplier for p in new_pos]

	for po in new_pos:
		if po.supplier == "Southern Fruit Supply":
			# Verify warehouse belongs to aggregation company (Chelsea Fruit Co)
			for item in po.items:
				wh_company = frappe.get_value("Warehouse", item.warehouse, "company")
				assert wh_company == po.company, f"Warehouse company mismatch: {wh_company} != {po.company}"
		elif po.supplier == "Freedom Provisions":
			for item in po.items:
				wh_company = frappe.get_value("Warehouse", item.warehouse, "company")
				assert wh_company == po.company, f"Warehouse company mismatch: {wh_company} != {po.company}"
		else:
			raise AssertionError(f"Unexpected supplier {po.supplier} in new POs")
		frappe.delete_doc("Purchase Order", po.name)
