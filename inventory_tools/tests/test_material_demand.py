import frappe
import pytest
from frappe.utils import flt, getdate

from inventory_tools.inventory_tools.report.material_demand.material_demand import (
	execute as execute_material_demand,
)


@pytest.mark.order(20)
def test_report_po_without_aggregation():
	filters = frappe._dict(
		{"end_date": getdate(), "price_list": "Bakery Buying", "company": "Ambrosia Pie Company"}
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


@pytest.mark.order(21)
def test_report_item_based_without_aggregation():
	filters = frappe._dict(
		{"end_date": getdate(), "price_list": "Bakery Buying", "company": "Ambrosia Pie Company"}
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


@pytest.mark.order(22)
def test_report_po_with_aggregation_and_no_aggregation_warehouse():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.purchase_order_aggregation_company = settings.name
	settings.aggregated_purchasing_warehouse = None
	settings.update_warehouse_path = True
	settings.save()

	filters = frappe._dict({"end_date": getdate(), "price_list": "Bakery Buying"})
	columns, rows = execute_material_demand(filters)
	assert len(rows) == 50
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

	pos = [frappe.get_doc("Purchase Order", p) for p in frappe.get_all("Purchase Order")]
	assert "Unity Bakery Supply" not in [p.get("supplier") for p in pos]
	for po in pos:
		if po.supplier == "Southern Fruit Supply":
			assert po.grand_total == flt(765.90, 2)
			for item in po.items:
				mr_wh = frappe.get_value("Material Request Item", item.material_request_item, "warehouse")
				assert item.warehouse == mr_wh

		elif po.supplier == "Freedom Provisions":
			assert po.grand_total == flt(439.89, 2)
			for item in po.items:
				mr_wh = frappe.get_value("Material Request Item", item.material_request_item, "warehouse")
				assert item.warehouse == mr_wh

		else:
			raise AssertionError(f"{po.supplier} should not be in this test")
		frappe.delete_doc("Purchase Order", po.name)


@pytest.mark.order(23)
def test_report_po_with_aggregation_and_aggregation_warehouse():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.purchase_order_aggregation_company = settings.name
	settings.aggregated_purchasing_warehouse = "Stores - CFC"
	settings.update_warehouse_path = True
	settings.save()

	filters = frappe._dict({"end_date": getdate(), "price_list": "Bakery Buying"})
	columns, rows = execute_material_demand(filters)
	assert len(rows) == 50
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

	pos = [frappe.get_doc("Purchase Order", p) for p in frappe.get_all("Purchase Order")]
	assert "Unity Bakery Supply" not in [p.get("supplier") for p in pos]
	for po in pos:
		if po.supplier == "Southern Fruit Supply":
			assert po.grand_total == flt(765.90, 2)
			for item in po.items:
				wh_company = frappe.get_value("Warehouse", item.warehouse, "company")
				assert wh_company == po.company

		elif po.supplier == "Freedom Provisions":
			assert po.grand_total == flt(439.89, 2)
			for item in po.items:
				wh_company = frappe.get_value("Warehouse", item.warehouse, "company")
				assert wh_company == po.company

		else:
			raise AssertionError(f"{po.supplier} should not be in this test")
		frappe.delete_doc("Purchase Order", po.name)
