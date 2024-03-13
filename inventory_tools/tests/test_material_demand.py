import frappe
import pytest
from frappe.utils import flt, getdate

from inventory_tools.inventory_tools.report.material_demand.material_demand import (
	execute as execute_material_demand,
)


def test_report_po_without_aggregation():
	filters = frappe._dict(
		{"end_date": getdate(), "price_list": "Bakery Buying", "company": "Ambrosia Pie Company"}
	)
	columns, rows = execute_material_demand(filters)
	assert len(rows) == 24
	assert rows[1].get("supplier") == "Chelsea Fruit Co"

	selected_rows = [row for row in rows if row.get("supplier") != "Unity Bakery Supply"]

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

	pos = frappe.get_all("Purchase Order", ["name", "supplier", "grand_total"])
	assert "Unity Bakery Supply" not in [p.get("supplier") for p in pos]
	for po in pos:
		if po.supplier == "Chelsea Fruit Co":
			assert po.grand_total == flt(501.07, 2)
		elif po.supplier == "Freedom Provisions":
			assert po.grand_total == flt(439.89, 2)
		else:
			raise AssertionError(f"{po.supplier} should not be in this test")
		frappe.delete_doc("Purchase Order", po.name)


def test_report_rfq_without_aggregation():
	filters = frappe._dict(
		{"end_date": getdate(), "price_list": "Bakery Buying", "company": "Ambrosia Pie Company"}
	)
	columns, rows = execute_material_demand(filters)
	assert len(rows) == 24
	assert rows[1].get("supplier") == "Chelsea Fruit Co"

	selected_rows = [row for row in rows if row.get("item_code")]

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


def test_report_item_based_without_aggregation():
	filters = frappe._dict(
		{"end_date": getdate(), "price_list": "Bakery Buying", "company": "Ambrosia Pie Company"}
	)
	columns, rows = execute_material_demand(filters)
	assert len(rows) == 24

	selected_rows = [
		row for row in rows if row.get("item_code") and row.get("supplier") != "Unity Bakery Supply"
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
			assert po.grand_total == flt(471.82, 2)
		elif po.supplier == "Freedom Provisions":
			assert po.grand_total == flt(439.89, 2)
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


@pytest.mark.skip()
def test_report_po_with_aggregation():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.purchase_order_aggregation_company = settings.name
	settings.aggregated_purchasing_warehouse = "Stores - CFC"
	settings.save()

	filters = frappe._dict({"end_date": getdate(), "price_list": "Bakery Buying"})
	columns, rows = execute_material_demand(filters)
	assert len(rows) == 24
	assert rows[1].get("supplier") == "Chelsea Fruit Co"

	selected_rows = [row for row in rows if row.get("supplier") != "Unity Bakery Supply"]

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

	pos = frappe.get_all("Purchase Order", ["name", "supplier", "grand_total"])
	assert "Unity Bakery Supply" not in [p.get("supplier") for p in pos]
	for po in pos:
		if po.supplier == "Chelsea Fruit Co":
			assert po.grand_total == flt(501.07, 2)
		elif po.supplier == "Freedom Provisions":
			assert po.grand_total == flt(439.89, 2)
		else:
			raise AssertionError(f"{po.supplier} should not be in this test")
		frappe.delete_doc("Purchase Order", po.name)
