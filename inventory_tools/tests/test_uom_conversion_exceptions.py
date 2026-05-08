# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import pytest

import inventory_tools.inventory_tools.uom_conversion_exceptions as uce


@pytest.mark.order(75)
def test_normalize_multiselect_filter_accepts_lists_and_json():
	assert uce.normalize_multiselect_filter(None) == []
	assert uce.normalize_multiselect_filter("") == []
	assert uce.normalize_multiselect_filter([" Nos ", "Box"]) == ["Nos", "Box"]
	assert uce.normalize_multiselect_filter('["Nos","Box"]') == ["Nos", "Box"]


@pytest.mark.order(76)
def test_row_matches_uom_filter_empty_means_all():
	assert uce.row_matches_uom_filter([], "A", "B") is True
	assert uce.row_matches_uom_filter(["X"], "A", "B") is False
	assert uce.row_matches_uom_filter(["A"], "A", "B") is True
	assert uce.row_matches_uom_filter(["B"], "A", "B") is True


@pytest.mark.order(77)
def test_row_matches_category_filter_sentinel_or_categories():
	uom_map = {
		"Kg": {"Mass"},
		"Lb": set(),
		"Box": {"Count"},
	}
	assert uce.row_matches_category_filter([], "Kg", "Lb", uom_map) is True
	assert (
		uce.row_matches_category_filter([uce.NOT_CATEGORIZED_SENTINEL], "Kg", "Lb", uom_map) is True
	)
	assert (
		uce.row_matches_category_filter([uce.NOT_CATEGORIZED_SENTINEL], "Kg", "Box", uom_map) is False
	)
	assert (
		uce.row_matches_category_filter([uce.NOT_CATEGORIZED_SENTINEL], "Kg", "Nos", uom_map) is True
	)
	assert uce.row_matches_category_filter(["Mass"], "Kg", "Lb", uom_map) is True
	assert uce.row_matches_category_filter(["Mass"], "Box", "Lb", uom_map) is False


@pytest.mark.order(78)
def test_is_undocumented_line_uom_with_detail_and_global_stub():
	meta = {
		"I1": {
			"name": "I1",
			"stock_uom": "Nos",
			"variant_of": None,
			"is_stock_item": 1,
		},
	}
	detail_pairs = {("I1", "Box")}

	assert (
		uce.is_undocumented_line_uom(
			"I1", "Box", "Nos", meta, detail_pairs, _global_check=lambda a, b: False
		)
		is False
	)

	assert (
		uce.is_undocumented_line_uom("I1", "Box", "Nos", meta, set(), _global_check=lambda a, b: False)
		is True
	)

	assert (
		uce.is_undocumented_line_uom("I1", "Box", "Nos", meta, set(), _global_check=lambda a, b: True)
		is False
	)

	assert uce.is_undocumented_line_uom("I1", "Nos", "Nos", meta, set()) is False


@pytest.mark.order(79)
def test_is_undocumented_non_stock_excluded():
	meta = {
		"SVC": {
			"name": "SVC",
			"stock_uom": "Nos",
			"variant_of": None,
			"is_stock_item": 0,
		},
	}
	assert uce.is_undocumented_line_uom("SVC", "Box", "Nos", meta, set()) is False
