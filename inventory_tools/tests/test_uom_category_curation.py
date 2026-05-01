# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import pytest

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
