# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import pytest
import frappe

import inventory_tools.inventory_tools.overrides.uom_category as uc


@pytest.mark.order(100)
def test_transactional_uom_link_scan_rules():
	"""Link parents used for Item/submitted UOM usage: include Item, skip Singles and UOM Conversion Factor."""

	branches = set(uc.collect_transactional_item_uom_link_branches())

	assert ("Item", "stock_uom") in branches

	singles = [r for r in uc.get_link_fields("UOM") if r.get("issingle")]
	assert (
		singles
	), "expect ERPNext metadata to expose Singles with Link-to-UOM (e.g. Global Defaults)"
	for row in singles:
		assert (row["parent"], row["fieldname"]) not in branches

	for fname in ("from_uom", "to_uom"):
		assert ("UOM Conversion Factor", fname) not in branches


@pytest.mark.order(101)
def test_unused_uom_names_from_usage_counts():
	cat_names = {"UOM-A", "UOM-B", "UOM-C"}
	usage_counts = {
		"UOM-A": {"total": 0, "by_doctype": {}},
		"UOM-B": {"total": 5, "by_doctype": {"Sales Order Item.uom": 5}},
		"UOM-C": {"total": 0, "by_doctype": {}},
	}

	def fake_conversion_uoms(categories):
		assert categories == ["Length"]
		return cat_names

	def fake_cross_used(exclude_categories, limit_to):
		assert exclude_categories == ["Length"]
		assert limit_to == cat_names
		return {"UOM-C"}

	original_conversion = uc.conversion_uoms_for_categories
	original_cross = uc.conversion_uoms_outside_categories
	try:
		uc.conversion_uoms_for_categories = fake_conversion_uoms
		uc.conversion_uoms_outside_categories = fake_cross_used
		unused = uc.unused_uom_names(["Length"], usage_counts)
	finally:
		uc.conversion_uoms_for_categories = original_conversion
		uc.conversion_uoms_outside_categories = original_cross

	assert unused == ["UOM-A"]


@pytest.mark.order(102)
def test_empty_usage_counts():
	counts = uc.empty_usage_counts({"UOM-A", "UOM-B"})
	assert counts["UOM-A"] == {"total": 0, "by_doctype": {}}
	assert counts["UOM-B"] == {"total": 0, "by_doctype": {}}


@pytest.mark.order(103)
def test_update_scan_eta_decreases_monotonically():
	first = uc.update_scan_eta(0, 1, 10, 2.0)
	second = uc.update_scan_eta(first, 2, 10, 5.0)
	assert first == 18.0
	assert second == 18.0


@pytest.mark.order(104)
def test_enqueue_uom_curation_doc_method_runs_inline_in_tests():
	called = []

	class FakeDoc:
		doctype = "UOM Category"
		name = "Length"

		def _run_uom_usage_scan(self):
			called.append("_run_uom_usage_scan")

	original_in_test = frappe.flags.in_test
	try:
		frappe.flags.in_test = True
		uc.enqueue_uom_curation_doc_method(FakeDoc(), "_run_uom_usage_scan")
	finally:
		frappe.flags.in_test = original_in_test

	assert called == ["_run_uom_usage_scan"]
