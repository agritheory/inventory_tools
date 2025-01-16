import json

import frappe
import pytest

from inventory_tools.inventory_tools.overrides.purchase_order import (
	make_purchase_invoices,
	make_purchase_receipts,
)


@pytest.mark.order(25)
def test_purchase_receipt_aggregation():
	# this should be called immediately after 'test_report_po_with_aggregation_and_no_aggregation_warehouse'
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")

	pos = [
		frappe.get_doc("Purchase Order", p) for p in frappe.get_all("Purchase Order", pluck="name")
	]
	for po in pos:
		items = [row.name for row in po.items]
		make_purchase_receipts(po.name, frappe.as_json(items))

	prs = [
		frappe.get_doc("Purchase Receipt", p) for p in frappe.get_all("Purchase Receipt", pluck="name")
	]
	for pr in prs:
		pr.submit()
		for row in pr.items:
			mr_company = frappe.get_value("Material Request", row.material_request, "company")
			po_company = frappe.get_value("Purchase Order", row.purchase_order, "company")
			assert mr_company == pr.company
			assert po.company == settings.purchase_order_aggregation_company


@pytest.mark.order(26)
def test_purchase_invoice_aggregation():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")

	pos = [
		frappe.get_doc("Purchase Order", p) for p in frappe.get_all("Purchase Order", pluck="name")
	]
	for po in pos:
		items = [row.name for row in po.items]
		make_purchase_invoices(po.name, frappe.as_json(items))

	pis = [
		frappe.get_doc("Purchase Invoice", p) for p in frappe.get_all("Purchase Invoice", pluck="name")
	]
	for pi in pis:
		pi.submit()
		for row in pi.items:
			material_request = frappe.get_value("Purchase Order Item", row.po_detail, "material_request")
			mr_company = frappe.get_value("Material Request", material_request, "company")
			po_company = frappe.get_value("Purchase Order", row.purchase_order, "company")
			assert mr_company == pi.company
			assert po.company == settings.purchase_order_aggregation_company
			# NOTE: PO company MAY BE different from MR and PI
