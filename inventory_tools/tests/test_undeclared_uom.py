# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import getdate

from inventory_tools.inventory_tools.report.undeclared_uom.undeclared_uom import execute

COMPANY = "Ambrosia Pie Company"
CUSTOMER = "Almacs Food Group"
WAREHOUSE = "Refrigerator - APC"
TEST_ITEM = "Undeclared UOM Test Berry"
DRAFT_ITEM = "Undeclared UOM Draft Berry"
MULTI_ITEM = "Undeclared UOM Multi Berry"
DESC_ITEM = "Undeclared UOM Desc Berry"


def report_filters(**overrides):
	filters = frappe._dict(
		{
			"company": COMPANY,
			"from_date": getdate().replace(month=1, day=1),
			"to_date": getdate(),
			"group_by": "UOM Pair",
			"status": ["Submitted"],
		}
	)
	filters.update(overrides)
	return filters


def line_rows(rows):
	return [row for row in rows if row.get("indent") == 1]


def header_rows(rows):
	return [row for row in rows if row.get("indent") == 0]


def cleanup_item_documents(item_code):
	for doctype in ("Sales Order", "Sales Invoice"):
		child_doctype = f"{doctype} Item"
		for row in frappe.get_all(child_doctype, filters={"item_code": item_code}, fields=["parent"]):
			if not frappe.db.exists(doctype, row.parent):
				continue
			doc = frappe.get_doc(doctype, row.parent)
			if doc.docstatus == 1:
				doc.cancel()
			frappe.delete_doc(doctype, row.parent, force=1)


def cleanup_test_item(item_code):
	cleanup_item_documents(item_code)
	if frappe.db.exists("Item", item_code):
		frappe.delete_doc("Item", item_code, force=1)


def make_test_item(item_code, stock_uom="Kg", extra_uoms=None):
	cleanup_test_item(item_code)
	item = frappe.new_doc("Item")
	item.item_code = item.item_name = item_code
	item.item_group = "Ingredients"
	item.stock_uom = stock_uom
	item.is_stock_item = 1
	item.is_sales_item = 1
	item.valuation_rate = 1
	item.append("uoms", {"uom": stock_uom, "conversion_factor": 1})
	if extra_uoms:
		for uom, conversion_factor in extra_uoms.items():
			item.append("uoms", {"uom": uom, "conversion_factor": conversion_factor})
	item.append(
		"item_defaults",
		{"company": COMPANY, "default_warehouse": WAREHOUSE},
	)
	item.save()
	return item


def make_sales_order(item_code, uom, qty=5, submit=True):
	so = frappe.new_doc("Sales Order")
	so.company = COMPANY
	so.customer = CUSTOMER
	so.transaction_date = getdate()
	so.delivery_date = getdate()
	so.append(
		"items",
		{
			"item_code": item_code,
			"qty": qty,
			"warehouse": WAREHOUSE,
		},
	)
	so.save()
	so.items[0].uom = uom
	so.items[0].conversion_factor = 1
	so.save()
	if submit:
		so.submit()
	return so


def findings_for_item(item_code, **filter_overrides):
	columns, rows = execute(report_filters(item_code=item_code, **filter_overrides))
	return line_rows(rows)


@pytest.mark.order(130)
def test_submitted_pound_on_kg_only_item_is_a_finding():
	make_test_item(TEST_ITEM, stock_uom="Kg")
	so = make_sales_order(TEST_ITEM, uom="Pound")

	columns, rows = execute(report_filters())
	findings = line_rows(rows)
	headers = header_rows(rows)

	matching = [
		row
		for row in findings
		if row.item_code == TEST_ITEM and row.undeclared_uom == "Pound" and row.transaction == so.name
	]
	assert len(matching) == 1
	assert matching[0]["stock_uom"] == "Kg"
	assert matching[0]["identity_conversion"] == 1
	assert any(header["group_label"] == "Pound → Kg" for header in headers)


@pytest.mark.order(131)
def test_stock_uom_line_is_not_a_finding():
	make_sales_order(TEST_ITEM, uom="Kg")

	findings = findings_for_item(TEST_ITEM)
	pound_findings = [row for row in findings if row.undeclared_uom == "Pound"]
	kg_findings = [row for row in findings if row.undeclared_uom == "Kg"]

	assert pound_findings
	assert not kg_findings


@pytest.mark.order(132)
def test_adding_uom_to_conversion_table_removes_finding():
	item = frappe.get_doc("Item", TEST_ITEM)
	item.append("uoms", {"uom": "Pound", "conversion_factor": 2.20462})
	item.save()

	findings = findings_for_item(TEST_ITEM)
	assert not [row for row in findings if row.undeclared_uom == "Pound"]


@pytest.mark.order(133)
def test_draft_status_filter():
	make_test_item(DRAFT_ITEM, stock_uom="Kg")
	make_sales_order(DRAFT_ITEM, uom="Pound", submit=False)

	submitted_findings = findings_for_item(DRAFT_ITEM, status=["Submitted"])
	draft_findings = findings_for_item(DRAFT_ITEM, status=["Draft"])

	assert not submitted_findings
	assert len(draft_findings) == 1
	assert draft_findings[0].undeclared_uom == "Pound"


@pytest.mark.order(134)
def test_document_grouping_shows_one_header_for_multiple_lines():
	make_test_item(MULTI_ITEM, stock_uom="Kg")
	so = frappe.new_doc("Sales Order")
	so.company = COMPANY
	so.customer = CUSTOMER
	so.transaction_date = getdate()
	so.delivery_date = getdate()
	for qty in (3, 7):
		so.append(
			"items",
			{
				"item_code": MULTI_ITEM,
				"qty": qty,
				"warehouse": WAREHOUSE,
			},
		)
	so.save()
	for row in so.items:
		row.uom = "Pound"
		row.conversion_factor = 1
	so.save()
	so.submit()

	columns, rows = execute(report_filters(group_by="Document", item_code=MULTI_ITEM))
	headers = header_rows(rows)
	findings = line_rows(rows)

	assert len(headers) == 1
	assert headers[0]["group_label"] == f"Sales Order {so.name}"
	assert headers[0]["line_count"] == 2
	assert len(findings) == 2
	assert {row.transaction for row in findings} == {so.name}


@pytest.mark.order(135)
def test_description_only_line_is_ignored():
	make_test_item(DESC_ITEM, stock_uom="Kg")
	so = frappe.new_doc("Sales Order")
	so.company = COMPANY
	so.customer = CUSTOMER
	so.transaction_date = getdate()
	so.delivery_date = getdate()
	so.append(
		"items",
		{
			"item_code": DESC_ITEM,
			"qty": 2,
			"warehouse": WAREHOUSE,
		},
	)
	so.append("items", {"description": "Gift wrapping", "qty": 1})
	so.flags.ignore_mandatory = True
	so.save()
	so.items[0].uom = "Pound"
	so.items[0].conversion_factor = 1
	so.flags.ignore_mandatory = True
	so.save()
	so.flags.ignore_mandatory = True
	so.submit()

	findings = findings_for_item(DESC_ITEM)
	assert len(findings) == 1
	assert findings[0].undeclared_uom == "Pound"
