# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import flt, getdate

from erpnext.controllers.stock_controller import QualityInspectionRequiredError
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from erpnext.stock.doctype.material_request.material_request import make_purchase_order

from inventory_tools.tests.setup import create_quarantine_quality_control_data
from inventory_tools.inventory_tools.overrides.stock_entry import (
	make_quarantine_release_stock_entry,
)


@pytest.fixture(scope="module", autouse=True)
def quarantine_qc_data():
	"""Install quarantine warehouses, QC templates, and receive workflow (fixtured in QC tests only).

	Flour's manufacture-inspection configuration is scoped here (not in setup.py) so it doesn't
	bleed into other test modules (test_wo_subcontracting, test_operating_costs, etc.).
	"""
	settings = frappe._dict({"company": "Ambrosia Pie Company"})
	create_quarantine_quality_control_data(settings)

	# Configure Flour for manufacture inspection — scoped to this module only
	flour = frappe.get_doc("Item", "Flour")
	original_qi_template = flour.quality_inspection_template
	flour.quality_inspection_template = "Ingredient QC"
	flour.save()
	apc_default = next((d for d in flour.item_defaults if d.company == "Ambrosia Pie Company"), None)
	original_manufacture_flag = (
		apc_default.inspection_required_before_manufacture if apc_default else 0
	)
	if apc_default:
		apc_default.inspection_required_before_manufacture = 1
	else:
		flour.append(
			"item_defaults",
			{
				"company": "Ambrosia Pie Company",
				"default_warehouse": "Storeroom - APC",
				"inspection_required_before_manufacture": 1,
			},
		)
	flour.save()

	yield

	# Restore Flour to its pre-test state so other modules are not affected
	flour.reload()
	flour.quality_inspection_template = original_qi_template
	apc_default = next((d for d in flour.item_defaults if d.company == "Ambrosia Pie Company"), None)
	if apc_default:
		apc_default.inspection_required_before_manufacture = original_manufacture_flag
	flour.save()
	frappe.db.commit()


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
	po.buying_price_list = "Bakery Buying"
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

	# Button calls make_quarantine_release_stock_entry; verify draft SE is created correctly
	se_name = make_quarantine_release_stock_entry(qa.name)
	se = frappe.get_doc("Stock Entry", se_name)

	assert se.docstatus == 0  # Draft — user must review and submit
	assert se.items[0].s_warehouse == "Quarantine - CFC"
	assert se.items[0].t_warehouse == "Stores - CFC"
	assert se.items[0].qty == full_qty  # full PR qty, not sample_size


@pytest.mark.order(14)
def test_release_from_quarantine_blocked_when_not_accepted():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_quarantine_workflow = 1
	settings.save()

	_po, pr = create_bayberry_po_pr(submit_pr=True)

	qa = create_quality_inspection(pr.name, status="Rejected")
	qa.submit()

	# Button should raise when QI is not Accepted
	with pytest.raises(frappe.ValidationError):
		make_quarantine_release_stock_entry(qa.name)

	qty_in_quarantine = frappe.db.sql(
		"""
		SELECT sum(actual_qty) FROM tabBin
		WHERE warehouse = 'Quarantine - CFC' AND item_code = 'Bayberry'
		""",
		as_dict=False,
	)[0][0]
	assert qty_in_quarantine > 0


@pytest.mark.order(15)
def test_release_from_quarantine_blocked_when_workflow_disabled():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_quarantine_workflow = 1
	settings.save()

	_po, pr = create_bayberry_po_pr(submit_pr=True)

	qa = create_quality_inspection(pr.name, status="Accepted")
	qa.submit()

	settings.enable_quarantine_workflow = 0
	settings.save()

	# Button should raise when quarantine workflow is disabled
	with pytest.raises(frappe.ValidationError):
		make_quarantine_release_stock_entry(qa.name)

	settings.enable_quarantine_workflow = 1
	settings.save()


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


def create_flour_manufacture_se(submit_se=True):
	"""Create Material Transfer for Manufacture SE for Flour in APC.

	Returns an unsaved in-memory doc when submit_se=False (mirrors create_bayberry_po_pr).
	"""
	se = frappe.new_doc("Stock Entry")
	se.company = "Ambrosia Pie Company"
	se.stock_entry_type = "Material Transfer for Manufacture"
	se.append(
		"items",
		{
			"item_code": "Flour",
			"qty": 10,
			"s_warehouse": "Storeroom - APC",
			"t_warehouse": "Kitchen - APC",
			"uom": "Pound",
		},
	)
	if submit_se:
		se.submit()
	return se


def create_se_quality_inspection(se_name, item_code="Flour", sample_size=1, status="Accepted"):
	"""Create QI for a Stock Entry reference (manufacture path)."""
	qa = frappe.new_doc("Quality Inspection")
	qa.report_date = getdate()
	qa.inspection_type = "In Process"
	qa.reference_type = "Stock Entry"
	qa.reference_name = se_name
	qa.item_code = item_code
	qa.sample_size = sample_size
	qa.quality_inspection_template = "Ingredient QC"
	qa.inspected_by = frappe.session.user
	qa.status = status
	reading_val = "999" if status == "Rejected" else "50"
	qa.append(
		"readings",
		{"specification": "Weight", "min_value": 0, "max_value": 100, "reading_1": reading_val},
	)
	qa.save()
	return qa


def get_release_transfers_for_qi(qi_name):
	"""Return Material Transfer SE names created by make_quarantine_release_stock_entry for a QI."""
	parent_names = frappe.get_all(
		"Stock Entry Detail",
		filters={"reference_doctype": "Quality Inspection", "reference_name": qi_name},
		pluck="parent",
	)
	return [
		n
		for n in set(parent_names)
		if frappe.db.get_value("Stock Entry", n, "stock_entry_type") == "Material Transfer"
	]


@pytest.mark.order(17)
def test_manufacture_se_routes_to_quarantine():
	apc_settings = frappe.get_doc("Inventory Tools Settings", "Ambrosia Pie Company")
	apc_settings.enable_quarantine_workflow = 1
	apc_settings.save()

	se = create_flour_manufacture_se(submit_se=True)

	flour_row = next(r for r in se.items if r.item_code == "Flour")
	assert flour_row.t_warehouse == "Quarantine - APC"
	assert flour_row.intended_warehouse == "Kitchen - APC"

	sle_wh = frappe.db.get_value(
		"Stock Ledger Entry",
		{
			"voucher_type": "Stock Entry",
			"voucher_no": se.name,
			"item_code": "Flour",
			"actual_qty": [">", 0],
		},
		"warehouse",
	)
	assert sle_wh == "Quarantine - APC"


@pytest.mark.order(18)
def test_manufacture_se_bypasses_quarantine_when_disabled():
	apc_settings = frappe.get_doc("Inventory Tools Settings", "Ambrosia Pie Company")
	apc_settings.enable_quarantine_workflow = 0
	apc_settings.save()

	se = create_flour_manufacture_se(submit_se=False)

	with pytest.raises((QualityInspectionRequiredError, frappe.ValidationError)):
		se.submit()


@pytest.mark.order(19)
def test_release_from_quarantine_on_se_accepted_qi():
	apc_settings = frappe.get_doc("Inventory Tools Settings", "Ambrosia Pie Company")
	apc_settings.enable_quarantine_workflow = 1
	apc_settings.save()

	se = create_flour_manufacture_se(submit_se=True)
	flour_row = next(r for r in se.items if r.item_code == "Flour")
	full_qty = flour_row.qty

	qa = create_se_quality_inspection(se.name, status="Accepted")
	qa.submit()

	release_se_name = make_quarantine_release_stock_entry(qa.name)
	release_se = frappe.get_doc("Stock Entry", release_se_name)

	assert release_se.docstatus == 0  # Draft for user review
	assert release_se.items[0].s_warehouse == "Quarantine - APC"
	assert release_se.items[0].t_warehouse == "Kitchen - APC"
	assert release_se.items[0].qty == full_qty


@pytest.mark.order(20)
def test_release_from_quarantine_blocked_on_se_rejected_qi():
	apc_settings = frappe.get_doc("Inventory Tools Settings", "Ambrosia Pie Company")
	apc_settings.enable_quarantine_workflow = 1
	apc_settings.save()

	se = create_flour_manufacture_se(submit_se=True)

	qa = create_se_quality_inspection(se.name, status="Rejected")
	qa.submit()

	with pytest.raises(frappe.ValidationError):
		make_quarantine_release_stock_entry(qa.name)

	qty_in_quarantine = frappe.db.sql(
		"""
		SELECT sum(actual_qty) FROM tabBin
		WHERE warehouse = 'Quarantine - APC' AND item_code = 'Flour'
		""",
		as_dict=False,
	)[0][0]
	assert qty_in_quarantine > 0


@pytest.mark.order(21)
def test_release_se_is_draft_with_qi_reference():
	"""Draft SE from the Release button carries QI reference so block_issue_from_quarantine allows it."""
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_quarantine_workflow = 1
	settings.save()

	_po, pr = create_bayberry_po_pr(submit_pr=True)

	qa = create_quality_inspection(pr.name, status="Accepted")
	qa.submit()

	se_name = make_quarantine_release_stock_entry(qa.name)
	se = frappe.get_doc("Stock Entry", se_name)

	assert se.docstatus == 0
	assert se.items[0].reference_doctype == "Quality Inspection"
	assert se.items[0].reference_name == qa.name


@pytest.mark.order(22)
def test_cancel_pr_while_in_quarantine():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_quarantine_workflow = 1
	settings.save()

	_po, pr = create_bayberry_po_pr(submit_pr=True)

	bayberry_row = next(r for r in pr.items if r.item_code == "Bayberry")
	assert bayberry_row.warehouse == "Quarantine - CFC"
	received_qty = bayberry_row.qty

	qty_before = flt(
		frappe.db.sql(
			"SELECT sum(actual_qty) FROM `tabBin` WHERE warehouse=%s AND item_code=%s",
			("Quarantine - CFC", "Bayberry"),
			as_dict=False,
		)[0][0]
		or 0
	)

	pr.reload()
	pr.cancel()

	qty_after = flt(
		frappe.db.sql(
			"SELECT sum(actual_qty) FROM `tabBin` WHERE warehouse=%s AND item_code=%s",
			("Quarantine - CFC", "Bayberry"),
			as_dict=False,
		)[0][0]
		or 0
	)
	assert qty_after == qty_before - received_qty


@pytest.mark.order(23)
def test_block_issue_from_quarantine_prevents_manual_se():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_quarantine_workflow = 1
	settings.block_issue_from_quarantine = 1
	settings.save()

	se = frappe.new_doc("Stock Entry")
	se.company = "Chelsea Fruit Co"
	se.stock_entry_type = "Material Issue"
	se.append(
		"items",
		{
			"item_code": "Bayberry",
			"qty": 1,
			"s_warehouse": "Quarantine - CFC",
			"uom": "Pound",
			"basic_rate": 1.0,
		},
	)
	se.save()

	with pytest.raises(frappe.ValidationError):
		se.submit()

	settings.block_issue_from_quarantine = 0
	settings.save()


@pytest.mark.order(24)
def test_block_issue_allows_qi_referenced_release():
	"""block_issue_from_quarantine must not prevent submitting a release SE created by the button."""
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_quarantine_workflow = 1
	settings.block_issue_from_quarantine = 1
	settings.save()

	_po, pr = create_bayberry_po_pr(submit_pr=True)

	qa = create_quality_inspection(pr.name, status="Accepted")
	qa.submit()

	se_name = make_quarantine_release_stock_entry(qa.name)
	se = frappe.get_doc("Stock Entry", se_name)

	# User reviews the draft, then submits — block_issue_from_quarantine must allow it through
	se.submit()
	assert frappe.db.get_value("Stock Entry", se_name, "docstatus") == 1

	settings.block_issue_from_quarantine = 0
	settings.save()


@pytest.mark.order(25)
def test_multi_item_pr_partial_quarantine_routing():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_quarantine_workflow = 1
	settings.save()

	# Cocoplum has no inspection_required_before_purchase for CFC after test 16 cleanup
	mr = frappe.new_doc("Material Request")
	mr.company = "Chelsea Fruit Co"
	mr.material_request_type = "Purchase"
	mr.transaction_date = getdate()
	mr.schedule_date = getdate()
	mr.append(
		"items", {"item_code": "Bayberry", "qty": 50, "warehouse": "Stores - CFC", "uom": "Pound"}
	)
	mr.append(
		"items", {"item_code": "Cocoplum", "qty": 20, "warehouse": "Stores - CFC", "uom": "Pound"}
	)
	mr.submit()

	po = make_purchase_order(mr.name)
	po.supplier = "Southern Fruit Supply"
	po.buying_price_list = "Bakery Buying"
	po.save()
	po.submit()

	pr = make_purchase_receipt(po.name)
	pr.submit()

	bayberry_row = next(r for r in pr.items if r.item_code == "Bayberry")
	cocoplum_row = next(r for r in pr.items if r.item_code == "Cocoplum")

	assert bayberry_row.warehouse == "Quarantine - CFC"
	assert bayberry_row.intended_warehouse == "Stores - CFC"

	assert cocoplum_row.warehouse == "Stores - CFC"
	assert not cocoplum_row.intended_warehouse


@pytest.mark.order(26)
def test_release_no_intended_warehouse_raises():
	"""When intended_warehouse is absent on the reference doc, make_quarantine_release_stock_entry raises."""
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_quarantine_workflow = 1
	settings.save()

	# Create a plain Material Transfer (not via handle_pr/se_quarantine) that lands Bayberry
	# in the quarantine warehouse — no intended_warehouse is set on the row.
	se = frappe.new_doc("Stock Entry")
	se.company = "Chelsea Fruit Co"
	se.stock_entry_type = "Material Transfer"
	se.append(
		"items",
		{
			"item_code": "Bayberry",
			"qty": 5,
			"s_warehouse": "Stores - CFC",
			"t_warehouse": "Quarantine - CFC",
			"uom": "Pound",
		},
	)
	se.save()
	se.submit()

	qa = frappe.new_doc("Quality Inspection")
	qa.report_date = getdate()
	qa.inspection_type = "In Process"
	qa.reference_type = "Stock Entry"
	qa.reference_name = se.name
	qa.item_code = "Bayberry"
	qa.sample_size = 1
	qa.quality_inspection_template = "Fruit QC"
	qa.inspected_by = frappe.session.user
	qa.status = "Accepted"
	qa.append(
		"readings",
		{"specification": "Weight", "min_value": 0, "max_value": 100, "reading_1": "50"},
	)
	qa.save()
	qa.submit()

	with pytest.raises(frappe.ValidationError):
		make_quarantine_release_stock_entry(qa.name)
