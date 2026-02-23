# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import getdate

from erpnext.controllers.stock_controller import QualityInspectionRequiredError
from inventory_tools.tests.setup import create_quarantine_quality_control_data


@pytest.fixture(scope="module", autouse=True)
def quarantine_qc_data():
	"""Install quarantine warehouses, QC templates, and receive workflow (fixtured in QC tests only)."""
	settings = frappe._dict({"company": "Ambrosia Pie Company"})
	create_quarantine_quality_control_data(settings)


from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from erpnext.stock.doctype.material_request.material_request import make_purchase_order


def create_bayberry_po_pr(submit_pr=True):
	"""Create MR -> PO -> PR for Bayberry. Returns (po, pr)."""
	mr = frappe.new_doc("Material Request")
	mr.company = "Chelsea Fruit Co"
	mr.material_request_type = "Purchase"
	mr.transaction_date = getdate()
	mr.schedule_date = getdate()
	mr.append(
		"items", {"item_code": "Bayberry", "qty": 100, "warehouse": "Stores - CFC", "uom": "Pound"}
	)
	mr.submit()

	po = make_purchase_order(mr.name)
	po.supplier = "Southern Fruit Supply"
	po.save()
	po.submit()

	pr = make_purchase_receipt(po.name)
	if submit_pr:
		pr.submit()
	return po, pr


def create_quality_inspection(pr_name, item_code="Bayberry", sample_size=5, status="Accepted"):
	"""Create QI for Fruit QC template (Weight param, 0-100 range)."""
	qa = frappe.new_doc("Quality Inspection")
	qa.report_date = getdate()
	qa.inspection_type = "Incoming"
	qa.reference_type = "Purchase Receipt"
	qa.reference_name = pr_name
	qa.item_code = item_code
	qa.sample_size = sample_size
	qa.quality_inspection_template = "Fruit QC"
	qa.inspected_by = frappe.session.user
	qa.status = status
	# Use out-of-range reading when Rejected so inspect_and_set_status doesn't overwrite status
	reading_val = "999" if status == "Rejected" else "50"
	qa.append(
		"readings",
		{"specification": "Weight", "min_value": 0, "max_value": 100, "reading_1": reading_val},
	)
	qa.save()
	return qa


@pytest.mark.order(11)
def test_purchase_receipt_routes_to_quarantine_when_enabled():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_quarantine_workflow = 1
	settings.save()

	_po, pr = create_bayberry_po_pr(submit_pr=True)

	bayberry_row = next(r for r in pr.items if r.item_code == "Bayberry")
	assert bayberry_row.warehouse == "Quarantine - CFC"
	assert bayberry_row.intended_warehouse == "Stores - CFC"
	assert not bayberry_row.quality_inspection

	sle = frappe.db.get_value(
		"Stock Ledger Entry",
		{"voucher_type": "Purchase Receipt", "voucher_no": pr.name, "item_code": "Bayberry"},
		"warehouse",
	)
	assert sle == "Quarantine - CFC"


@pytest.mark.order(12)
def test_purchase_receipt_bypasses_quarantine_when_disabled():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_quarantine_workflow = 0
	settings.save()

	_po, pr = create_bayberry_po_pr(submit_pr=False)

	with pytest.raises((QualityInspectionRequiredError, frappe.ValidationError)):
		pr.submit()


@pytest.mark.order(13)
def test_release_from_quarantine_on_quality_inspection_accept():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_quarantine_workflow = 1
	settings.save()

	_po, pr = create_bayberry_po_pr(submit_pr=True)

	bayberry_row = next(r for r in pr.items if r.item_code == "Bayberry")
	full_qty = bayberry_row.qty

	qa = create_quality_inspection(pr.name, sample_size=5, status="Accepted")
	qa.submit()

	# reference_doctype is on Stock Entry Detail (child), not Stock Entry
	parent_names = frappe.get_all(
		"Stock Entry Detail",
		filters={
			"reference_doctype": "Quality Inspection",
			"reference_name": qa.name,
		},
		pluck="parent",
	)
	transfers = [
		n
		for n in set(parent_names)
		if frappe.db.get_value("Stock Entry", n, "stock_entry_type") == "Material Transfer"
	]
	assert len(transfers) == 1

	se = frappe.get_doc("Stock Entry", transfers[0])
	assert se.items[0].s_warehouse == "Quarantine - CFC"
	assert se.items[0].t_warehouse == "Stores - CFC"
	assert se.items[0].qty == full_qty  # full PR qty, not sample_size


@pytest.mark.order(14)
def test_release_from_quarantine_skipped_when_not_accepted():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_quarantine_workflow = 1
	settings.save()

	_po, pr = create_bayberry_po_pr(submit_pr=True)

	qa = create_quality_inspection(pr.name, status="Rejected")
	qa.submit()

	parent_names = frappe.get_all(
		"Stock Entry Detail",
		filters={
			"reference_doctype": "Quality Inspection",
			"reference_name": qa.name,
		},
		pluck="parent",
	)
	transfers = [
		n
		for n in set(parent_names or [])
		if frappe.db.get_value("Stock Entry", n, "stock_entry_type") == "Material Transfer"
	]
	assert len(transfers) == 0

	qty_in_quarantine = frappe.db.sql(
		"""
		SELECT sum(actual_qty) FROM tabBin
		WHERE warehouse = 'Quarantine - CFC' AND item_code = 'Bayberry'
		""",
		as_dict=False,
	)[0][0]
	assert qty_in_quarantine > 0


@pytest.mark.order(15)
def test_release_from_quarantine_skipped_when_workflow_disabled():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_quarantine_workflow = 1
	settings.save()

	_po, pr = create_bayberry_po_pr(submit_pr=True)

	qa = create_quality_inspection(pr.name, status="Accepted")
	settings.enable_quarantine_workflow = 0
	settings.save()

	qa.submit()

	parent_names = frappe.get_all(
		"Stock Entry Detail",
		filters={
			"reference_doctype": "Quality Inspection",
			"reference_name": qa.name,
		},
		pluck="parent",
	)
	transfers = [
		n
		for n in set(parent_names or [])
		if frappe.db.get_value("Stock Entry", n, "stock_entry_type") == "Material Transfer"
	]
	assert len(transfers) == 0


@pytest.mark.order(16)
def test_missing_quarantine_warehouse_throws():
	# Use Cocoplum with template that has no quarantine_warehouse; clear settings default
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_quarantine_workflow = 1
	settings.default_quarantine_warehouse = None
	settings.save()

	# Create template without quarantine for this test
	if not frappe.db.exists("Quality Inspection Template", "No Quarantine QC"):
		qit = frappe.new_doc("Quality Inspection Template")
		qit.quality_inspection_template_name = "No Quarantine QC"
		qit.append(
			"item_quality_inspection_parameter",
			{"specification": "Weight", "numeric": 1, "min_value": 0, "max_value": 100},
		)
		qit.insert()

	# Temporarily configure Cocoplum with no-quarantine template and inspection required
	cocoplum = frappe.get_doc("Item", "Cocoplum")
	original_template = cocoplum.quality_inspection_template
	cocoplum.quality_inspection_template = "No Quarantine QC"
	cocoplum.save()

	# Ensure Cocoplum has inspection_required_before_purchase for Chelsea Fruit Co
	cfc_default = next((d for d in cocoplum.item_defaults if d.company == "Chelsea Fruit Co"), None)
	added_cfc_default = False
	if cfc_default:
		cfc_default.inspection_required_before_purchase = 1
	else:
		cocoplum.append(
			"item_defaults",
			{
				"company": "Chelsea Fruit Co",
				"default_warehouse": "Stores - CFC",
				"inspection_required_before_purchase": 1,
			},
		)
		added_cfc_default = True
	cocoplum.save()

	mr = frappe.new_doc("Material Request")
	mr.company = "Chelsea Fruit Co"
	mr.material_request_type = "Purchase"
	mr.transaction_date = getdate()
	mr.schedule_date = getdate()
	mr.append(
		"items", {"item_code": "Cocoplum", "qty": 10, "warehouse": "Stores - CFC", "uom": "Pound"}
	)
	mr.submit()

	po = make_purchase_order(mr.name)
	po.supplier = "Southern Fruit Supply"
	po.save()
	po.submit()
	pr = make_purchase_receipt(po.name)

	with pytest.raises(Exception) as exc_info:
		pr.submit()
	assert "No Quarantine Warehouse configured" in str(exc_info.value)

	# Cleanup
	pr.delete()
	po.reload()
	po.cancel()
	mr.reload()
	mr.cancel()
	cocoplum.reload()
	cocoplum.quality_inspection_template = original_template
	cfc_default = next((d for d in cocoplum.item_defaults if d.company == "Chelsea Fruit Co"), None)
	if cfc_default:
		cfc_default.inspection_required_before_purchase = 0
	elif added_cfc_default:
		cocoplum.item_defaults = [d for d in cocoplum.item_defaults if d.company != "Chelsea Fruit Co"]
	cocoplum.save()
	settings.default_quarantine_warehouse = "Quarantine - CFC"
	settings.save()
