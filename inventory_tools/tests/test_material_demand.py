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
	settings.aggregated_purchasing_warehouse = "Receiving - CFC"
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


def clear_purchase_order_aggregation():
	for company in ("Chelsea Fruit Co", "Ambrosia Pie Company"):
		settings = frappe.get_doc("Inventory Tools Settings", company)
		settings.purchase_order_aggregation_company = None
		settings.aggregated_purchasing_warehouse = None
		settings.save()


def create_pos_from_material_demand(company, filters, rows, companies=None):
	args = {
		"company": company,
		"email_template": "",
		"filters": filters,
		"creation_type": "po",
		"rows": frappe.as_json(rows),
	}
	if companies is not None:
		args["companies"] = companies
	frappe.call(
		"inventory_tools.inventory_tools.report.material_demand.material_demand.create",
		**args,
	)


def new_purchase_orders(existing_names):
	return [
		frappe.get_doc("Purchase Order", name)
		for name in set(frappe.get_all("Purchase Order", pluck="name")) - existing_names
	]


@pytest.mark.order(34)
def test_create_po_uses_company_filter_when_aggregation_is_unset():
	"""Ambrosia Pie Company filter creates POs for Ambrosia, not a blank aggregation company."""
	clear_purchase_order_aggregation()
	existing_pos = set(frappe.get_all("Purchase Order", pluck="name"))
	filters = frappe._dict(
		{"end_date": getdate(), "price_list": "Bakery Wholesale", "company": "Ambrosia Pie Company"}
	)
	columns, rows = execute_material_demand(filters)
	selected_rows = [
		row
		for row in rows
		if row.get("item_code")
		and row.get("supplier") not in ["Southern Fruit Supply", "Unity Bakery Supply"]
	]
	create_pos_from_material_demand("Ambrosia Pie Company", filters, selected_rows)

	new_pos = new_purchase_orders(existing_pos)
	assert new_pos, "Create PO should make at least one Purchase Order"
	for po in new_pos:
		assert po.company == "Ambrosia Pie Company"
		assert not po.multi_company_purchase_order
		for item in po.items:
			assert item.requesting_company == "Ambrosia Pie Company"
			assert item.material_request
		frappe.delete_doc("Purchase Order", po.name)


@pytest.mark.order(35)
def test_aggregated_po_keeps_requesting_company_from_material_request():
	"""Chelsea aggregation combines Southern Fruit Supply demand and stamps each line with the requesting company."""
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.purchase_order_aggregation_company = settings.name
	settings.aggregated_purchasing_warehouse = None
	settings.save()

	existing_pos = set(frappe.get_all("Purchase Order", pluck="name"))
	filters = frappe._dict({"end_date": getdate(), "price_list": "Bakery Wholesale"})
	columns, rows = execute_material_demand(filters)
	selected_rows = [
		row for row in rows if row.get("item_code") and row.get("supplier") == "Southern Fruit Supply"
	]
	create_pos_from_material_demand("Chelsea Fruit Co", filters, selected_rows)

	new_pos = new_purchase_orders(existing_pos)
	assert len(new_pos) == 1
	po = new_pos[0]
	assert po.company == "Chelsea Fruit Co"
	assert po.supplier == "Southern Fruit Supply"
	requesting = {item.requesting_company for item in po.items}
	assert "Ambrosia Pie Company" in requesting
	assert "Chelsea Fruit Co" in requesting
	assert po.multi_company_purchase_order
	for item in po.items:
		mr_company = frappe.get_value("Material Request", item.material_request, "company")
		assert item.requesting_company == mr_company
		mr_warehouse = frappe.get_value("Material Request Item", item.material_request_item, "warehouse")
		assert item.warehouse == mr_warehouse
	frappe.delete_doc("Purchase Order", po.name)
	clear_purchase_order_aggregation()


@pytest.mark.order(36)
def test_aggregated_warehouse_does_not_replace_requesting_company():
	"""Receiving - CFC overrides the line warehouse; requesting company still comes from the Material Request."""
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.purchase_order_aggregation_company = settings.name
	settings.aggregated_purchasing_warehouse = "Receiving - CFC"
	settings.save()

	existing_pos = set(frappe.get_all("Purchase Order", pluck="name"))
	filters = frappe._dict({"end_date": getdate(), "price_list": "Bakery Wholesale"})
	columns, rows = execute_material_demand(filters)
	selected_rows = [
		row for row in rows if row.get("item_code") and row.get("supplier") == "Southern Fruit Supply"
	]
	create_pos_from_material_demand("Chelsea Fruit Co", filters, selected_rows)

	new_pos = new_purchase_orders(existing_pos)
	assert len(new_pos) == 1
	po = new_pos[0]
	assert po.company == "Chelsea Fruit Co"
	assert po.multi_company_purchase_order
	for item in po.items:
		assert item.warehouse == "Receiving - CFC"
		mr_company = frappe.get_value("Material Request", item.material_request, "company")
		assert item.requesting_company == mr_company
	frappe.delete_doc("Purchase Order", po.name)
	clear_purchase_order_aggregation()


@pytest.mark.order(37)
def test_make_purchase_receipts_creates_one_pr_per_requesting_company():
	"""Create Purchase Receipts splits a multi-company Southern Fruit Supply PO by requesting company."""
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.purchase_order_aggregation_company = settings.name
	settings.aggregated_purchasing_warehouse = None
	settings.save()

	existing_pos = set(frappe.get_all("Purchase Order", pluck="name"))
	existing_prs = set(frappe.get_all("Purchase Receipt", pluck="name"))
	filters = frappe._dict({"end_date": getdate(), "price_list": "Bakery Wholesale"})
	columns, rows = execute_material_demand(filters)
	selected_rows = [
		row for row in rows if row.get("item_code") and row.get("supplier") == "Southern Fruit Supply"
	]
	create_pos_from_material_demand("Chelsea Fruit Co", filters, selected_rows)

	new_pos = new_purchase_orders(existing_pos)
	assert len(new_pos) == 1
	po = new_pos[0]
	try:
		po.submit()

		frappe.call(
			"inventory_tools.inventory_tools.overrides.purchase_order.make_purchase_receipts",
			docname=po.name,
			rows=frappe.as_json([item.name for item in po.items]),
		)
		new_prs = [
			frappe.get_doc("Purchase Receipt", name)
			for name in set(frappe.get_all("Purchase Receipt", pluck="name")) - existing_prs
		]
		pr_companies = {pr.company for pr in new_prs}
		assert pr_companies == {item.requesting_company for item in po.items}
		for pr in new_prs:
			assert pr.items
			assert frappe.get_cached_value("Cost Center", pr.cost_center, "company") == pr.company
			for pr_item in pr.items:
				po_item = next(item for item in po.items if item.name == pr_item.purchase_order_item)
				assert po_item.requesting_company == pr.company
				assert frappe.get_cached_value("Cost Center", pr_item.cost_center, "company") == pr.company
				mr_warehouse = frappe.db.get_value(
					"Material Request Item", pr_item.material_request_item, "warehouse"
				)
				assert pr_item.warehouse == mr_warehouse
				assert frappe.get_cached_value("Warehouse", pr_item.warehouse, "company") == pr.company
			frappe.delete_doc("Purchase Receipt", pr.name)
	finally:
		if po.docstatus == 1:
			po.cancel()
		frappe.delete_doc("Purchase Order", po.name)
		clear_purchase_order_aggregation()


@pytest.mark.order(38)
def test_aggregation_with_one_requesting_company_is_not_multi_company():
	"""A Chelsea-only selection on the aggregator is a normal PO, not a multi-company PO."""
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.purchase_order_aggregation_company = settings.name
	settings.aggregated_purchasing_warehouse = None
	settings.save()

	existing_pos = set(frappe.get_all("Purchase Order", pluck="name"))
	filters = frappe._dict({"end_date": getdate(), "price_list": "Bakery Wholesale"})
	columns, rows = execute_material_demand(filters)
	selected_rows = [
		row
		for row in rows
		if row.get("item_code")
		and row.get("supplier") == "Southern Fruit Supply"
		and row.get("company") == "Chelsea Fruit Co"
	]
	create_pos_from_material_demand("Chelsea Fruit Co", filters, selected_rows)

	new_pos = new_purchase_orders(existing_pos)
	assert len(new_pos) == 1
	po = new_pos[0]
	assert po.company == "Chelsea Fruit Co"
	assert not po.multi_company_purchase_order
	for item in po.items:
		assert item.requesting_company == "Chelsea Fruit Co"
	frappe.delete_doc("Purchase Order", po.name)
	clear_purchase_order_aggregation()


@pytest.mark.order(40)
def test_create_po_multi_select_companies_without_aggregation():
	"""Selecting Ambrosia and Chelsea without aggregation still combines Southern Fruit Supply onto one multi-company PO."""
	clear_purchase_order_aggregation()
	existing_pos = set(frappe.get_all("Purchase Order", pluck="name"))
	filters = frappe._dict({"end_date": getdate(), "price_list": "Bakery Wholesale"})
	columns, rows = execute_material_demand(filters)
	selected_rows = [
		row for row in rows if row.get("item_code") and row.get("supplier") == "Southern Fruit Supply"
	]
	create_pos_from_material_demand(
		"Ambrosia Pie Company",
		filters,
		selected_rows,
		companies=["Ambrosia Pie Company", "Chelsea Fruit Co"],
	)

	new_pos = new_purchase_orders(existing_pos)
	assert len(new_pos) == 1
	po = new_pos[0]
	assert po.company == "Ambrosia Pie Company"
	assert po.supplier == "Southern Fruit Supply"
	assert po.multi_company_purchase_order
	requesting = {item.requesting_company for item in po.items}
	assert "Ambrosia Pie Company" in requesting
	assert "Chelsea Fruit Co" in requesting
	frappe.delete_doc("Purchase Order", po.name)
