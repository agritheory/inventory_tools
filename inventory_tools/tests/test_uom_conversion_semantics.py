# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import pytest
from frappe.query_builder import DocType

import inventory_tools.inventory_tools.uom_conversion_semantics as ucs


@pytest.mark.order(70)
def test_contextual_basis_only_when_explicit():
	assert not ucs.is_contextual_conversion_factor({})
	assert not ucs.is_contextual_conversion_factor({"it_conversion_basis": None})
	assert not ucs.is_contextual_conversion_factor({"it_conversion_basis": ""})
	assert not ucs.is_contextual_conversion_factor({"it_conversion_basis": "fixed"})
	assert ucs.is_contextual_conversion_factor({"it_conversion_basis": "contextual"})
	assert ucs.is_contextual_conversion_factor({"it_conversion_basis": "  contextual  "})


@pytest.mark.order(71)
def test_strict_participation_matches_contract():
	row_ctx = {"it_conversion_basis": "contextual"}
	row_fixed = {"it_conversion_basis": "fixed"}
	row_empty = {}

	assert ucs.participates_in_strict_conversion_checks(row_ctx) is False
	assert ucs.participates_in_strict_conversion_checks(row_fixed) is True
	assert ucs.participates_in_strict_conversion_checks(row_empty) is True
	assert (
		ucs.participates_in_strict_conversion_checks({"it_conversion_basis": "typo-or-future"}) is True
	)


@pytest.mark.order(72)
def test_get_conversion_basis_normalizes_blank():
	assert ucs.get_conversion_basis({"it_conversion_basis": "fixed"}) == "fixed"
	assert ucs.get_conversion_basis({"it_conversion_basis": "  "}) is None


@pytest.mark.order(73)
def test_qb_where_clauses_include_expected_columns():
	ucf = DocType("UOM Conversion Factor")
	sql_strict = ucs.qb_uom_conversion_factor_strict_rows(ucf).get_sql()
	sql_ctx = ucs.qb_uom_conversion_factor_contextual_rows(ucf).get_sql()
	assert ucs.FIELD_CONVERSION_BASIS in sql_strict
	assert ucs.BASIS_CONTEXTUAL.casefold() in sql_strict.casefold()
	assert ucs.FIELD_CONVERSION_BASIS in sql_ctx
	assert ucs.BASIS_CONTEXTUAL.casefold() in sql_ctx.casefold()
