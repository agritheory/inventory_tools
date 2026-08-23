# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
import pytest

from inventory_tools.cartonization import (
	apply_policy,
	convert_stock_qty_to_physical_dimension_units,
	resolve_item_physical_dimension,
	run_cartonization,
	validate_2d_floor,
	validate_3d_fitted,
	validate_3d_volume,
	validate_weight,
)

# Fruit Storage 1 - CFC: 1.5m × 2.5m floor, 1.0m height, 5.0 kg max weight
CONTAINER = {
	"item_length": 1.5,
	"item_width": 2.5,
	"item_height": 1.0,
	"item_volume": 3.75,
	"item_weight": 5.0,
}

# Bilberry exterior dims (from item_dimensions.json): 1.25 × 0.83 × 0.42 m, 0.55 kg
# floor = 1.0375 m²,  volume ≈ 0.4358 m³
BILBERRY = {
	"item_code": "Bilberry",
	"item_length": 1.25,
	"item_width": 0.83,
	"item_height": 0.42,
	"item_volume": 0.43575,
	"item_weight": 0.55,
	"orientation": 1,
}


def make_items(item_template, qty):
	"""Return a list with a single item dict at the given qty."""
	item = dict(item_template)
	item["qty"] = qty
	return [item]


def make_doc(
	items_list, company="Chelsea Fruit Co", doctype="Stock Entry", warehouse="Fruit Storage 1 - CFC"
):
	"""Build a minimal synthetic document object for run_cartonization."""
	items = []

	for item in items_list:
		row = frappe._dict(
			{
				"item_code": item["item_code"],
				"qty": item["qty"],
				"warehouse": None,
				"s_warehouse": None,
				"t_warehouse": warehouse,
			}
		)

		for key in ("uom", "stock_uom", "conversion_factor", "transfer_qty"):
			if key in item:
				row[key] = item[key]

		items.append(row)

	return frappe._dict(
		{
			"company": company,
			"doctype": doctype,
			"items": items,
		}
	)


def configure_cfc_cartonization(mode, dimensional_policy, weight_policy="Ignore", doctypes=None):
	"""Configure Chelsea Fruit Co Inventory Tools Settings for cartonization tests."""
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_cartonization = 1
	settings.default_packing_mode = mode
	settings.floor_packing_policy = dimensional_policy if mode == "2D Floor" else "Ignore"
	settings.volumetric_policy = dimensional_policy if mode == "3D Volumetric" else "Ignore"
	settings.fitted_policy = dimensional_policy if mode == "3D Fitted" else "Ignore"
	settings.weight_validation = weight_policy
	settings.allow_rotation = 1
	settings.solver_timeout_seconds = 10
	settings.cartonization_doctypes = []
	for dt in doctypes or ["Stock Entry"]:
		settings.append("cartonization_doctypes", {"doctype_name": dt})
	settings.save()
	return settings


def disable_cfc_cartonization():
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_cartonization = 0
	settings.cartonization_doctypes = []
	settings.save()


@pytest.mark.order(75)
def test_validate_2d_floor_fits():
	items = make_items(BILBERRY, qty=3)
	result = validate_2d_floor(items, CONTAINER)
	assert result["fits"] is True
	assert result["used_area"] == pytest.approx(3 * BILBERRY["item_length"] * BILBERRY["item_width"])
	assert result["container_area"] == pytest.approx(
		CONTAINER["item_length"] * CONTAINER["item_width"]
	)
	assert result["utilization"] < 1.0


@pytest.mark.order(76)
def test_validate_2d_floor_fails():
	items = make_items(BILBERRY, qty=4)
	result = validate_2d_floor(items, CONTAINER)
	assert result["fits"] is False
	assert result["used_area"] > result["container_area"]
	assert result["utilization"] > 1.0


@pytest.mark.order(77)
def test_validate_3d_volume_fits():
	items = make_items(BILBERRY, qty=8)
	result = validate_3d_volume(items, CONTAINER)
	assert result["fits"] is True
	assert result["used_volume"] == pytest.approx(8 * BILBERRY["item_volume"], rel=1e-3)


@pytest.mark.order(78)
def test_validate_3d_volume_fails():
	items = make_items(BILBERRY, qty=9)
	result = validate_3d_volume(items, CONTAINER)
	assert result["fits"] is False
	assert result["used_volume"] > result["container_volume"]


@pytest.mark.order(79)
def test_validate_3d_fitted_fits():
	items = make_items(BILBERRY, qty=1)
	result = validate_3d_fitted(items, CONTAINER, allow_rotation=False, timeout=10)
	assert result["fits"] is True


@pytest.mark.order(80)
def test_validate_3d_fitted_fails():
	# An item that is 2.0 × 2.0 × 2.0 m cannot fit in 1.5 × 2.5 × 1.0 m container
	# (2.0 > 1.0 in height, no rotation can save it)
	oversized = {
		"item_code": "OversizedBox",
		"item_length": 2.0,
		"item_width": 2.0,
		"item_height": 2.0,
		"item_volume": 8.0,
		"item_weight": 1.0,
		"orientation": 0,
	}
	items = make_items(oversized, qty=1)
	result = validate_3d_fitted(items, CONTAINER, allow_rotation=False, timeout=10)
	assert result["fits"] is False


@pytest.mark.order(81)
def test_validate_3d_fitted_no_items():
	result = validate_3d_fitted([], CONTAINER, allow_rotation=False, timeout=10)
	assert result["fits"] is True
	assert result["status"] == "NO_ITEMS"


@pytest.mark.order(82)
def test_validate_weight_fits():
	items = make_items(BILBERRY, qty=9)
	result = validate_weight(items, CONTAINER)
	assert result["fits"] is True
	assert result["total_weight"] == pytest.approx(9 * BILBERRY["item_weight"])


@pytest.mark.order(83)
def test_validate_weight_fails():
	items = make_items(BILBERRY, qty=10)
	result = validate_weight(items, CONTAINER)
	assert result["fits"] is False
	assert result["total_weight"] == pytest.approx(10 * BILBERRY["item_weight"])
	assert result["max_weight"] == CONTAINER["item_weight"]


@pytest.mark.order(84)
def test_validate_weight_no_max_weight():
	container_no_weight = dict(CONTAINER)
	container_no_weight["item_weight"] = 0
	items = make_items(BILBERRY, qty=1000)
	result = validate_weight(items, container_no_weight)
	assert result["fits"] is True


@pytest.mark.order(85)
def test_apply_policy_ignore():
	apply_policy({"fits": False}, "Ignore", "test context")


@pytest.mark.order(86)
def test_apply_policy_fits_no_action():
	apply_policy({"fits": True}, "Error", "test context")
	apply_policy({"fits": True}, "Warn", "test context")


@pytest.mark.order(87)
def test_apply_policy_warn():
	with patch.object(frappe, "msgprint") as mock_msgprint:
		apply_policy({"fits": False}, "Warn", "test context")
		mock_msgprint.assert_called_once()
		call_args = mock_msgprint.call_args[0][0]
		assert "Cartonization" in call_args
		assert "test context" in call_args


@pytest.mark.order(88)
def test_apply_policy_error():
	with pytest.raises(frappe.ValidationError):
		apply_policy({"fits": False}, "Error", "test context")


@pytest.mark.order(89)
def test_run_cartonization_disabled():
	"""When cartonization is disabled, run_cartonization is a no-op."""
	settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	settings.enable_cartonization = 0
	settings.save()

	doc = make_doc(make_items(BILBERRY, qty=100))
	run_cartonization(doc)


@pytest.mark.order(90)
def test_run_cartonization_doctype_not_configured():
	"""When the doctype is not in cartonization_doctypes, validation is skipped."""
	configure_cfc_cartonization("2D Floor", "Error", doctypes=["Pick List"])

	try:
		doc = make_doc(make_items(BILBERRY, qty=100))
		run_cartonization(doc)
	finally:
		disable_cfc_cartonization()


@pytest.mark.order(91)
def test_run_cartonization_items_without_dimensions_skipped():
	"""Items with no Physical Dimension record are silently skipped."""
	configure_cfc_cartonization("2D Floor", "Error")

	try:
		doc = make_doc([{"item_code": "Bilberry", "qty": 100}])
		with patch("inventory_tools.cartonization.resolve_item_physical_dimension", return_value=None):
			run_cartonization(doc)
	finally:
		disable_cfc_cartonization()


@pytest.mark.order(92)
def test_run_cartonization_warehouse_exempt():
	"""A cartonization-exempt warehouse is skipped regardless of policy."""
	configure_cfc_cartonization("2D Floor", "Error")

	wh = frappe.get_doc("Warehouse", "Fruit Storage 1 - CFC")
	wh.cartonization_exempt = 1
	wh.save()

	try:
		doc = make_doc(make_items(BILBERRY, qty=100))
		run_cartonization(doc)
	finally:
		wh.reload()
		wh.cartonization_exempt = 0
		wh.save()
		disable_cfc_cartonization()


@pytest.mark.order(93)
def test_run_cartonization_2d_floor_warn_policy():
	"""Warn policy logs a message but does not block the operation."""
	configure_cfc_cartonization("2D Floor", "Warn")

	try:
		doc = make_doc(make_items(BILBERRY, qty=4))
		with patch.object(frappe, "msgprint") as mock_msgprint:
			run_cartonization(doc)
			mock_msgprint.assert_called()
			assert any("Cartonization" in str(call) for call in mock_msgprint.call_args_list)
	finally:
		disable_cfc_cartonization()


@pytest.mark.order(94)
def test_run_cartonization_2d_floor_error_policy():
	"""Error policy raises ValidationError when items overflow the container."""
	configure_cfc_cartonization("2D Floor", "Error")

	try:
		doc = make_doc(make_items(BILBERRY, qty=4))
		with pytest.raises(frappe.ValidationError) as exc_info:
			run_cartonization(doc)
		assert "Cartonization" in str(exc_info.value)
	finally:
		disable_cfc_cartonization()


@pytest.mark.order(95)
def test_run_cartonization_2d_floor_fits_no_error():
	"""When items fit, no error is raised even with Error policy."""
	configure_cfc_cartonization("2D Floor", "Error")

	try:
		doc = make_doc(make_items(BILBERRY, qty=3))
		run_cartonization(doc)
	finally:
		disable_cfc_cartonization()


@pytest.mark.order(96)
def test_run_cartonization_3d_volumetric_error_policy():
	"""3D Volumetric mode with Error policy blocks when volume overflows."""
	configure_cfc_cartonization("3D Volumetric", "Error")

	try:
		doc = make_doc(make_items(BILBERRY, qty=9))
		with pytest.raises(frappe.ValidationError):
			run_cartonization(doc)
	finally:
		disable_cfc_cartonization()


@pytest.mark.order(97)
def test_run_cartonization_weight_warn_policy():
	"""Weight validation Warn policy logs a message when weight is exceeded."""
	with patch.object(frappe, "msgprint") as mock_msgprint:
		apply_policy({"fits": False}, "Warn", "Fruit Storage 1 - CFC (weight)")
		mock_msgprint.assert_called_once()


@pytest.mark.order(98)
def test_run_cartonization_weight_error_policy():
	"""Weight validation Error policy raises when weight limit is exceeded."""
	with pytest.raises(frappe.ValidationError):
		apply_policy({"fits": False}, "Error", "Fruit Storage 1 - CFC (weight)")


@pytest.mark.order(99)
def test_run_cartonization_3d_fitted_overflow():
	"""
	End-to-end 3D Fitted test through the on_submit hook.

	Story: Finished Goods - CFC is temporarily resized to 2 m × 2 m × 1.5 m.
	Bilberry is temporarily resized to a 1 m³ cube.  Four boxes tile neatly on
	the 2×2 floor (4 fits), but a fifth cannot fit — stacking two high would
	require 2 m which exceeds the 1.5 m ceiling.  The failing submission is
	rejected by cartonization; the successful one is cancelled in cleanup.
	"""
	configure_cfc_cartonization("3D Fitted", "Error")

	wh_dim = frappe.get_doc(
		"Physical Dimension",
		{
			"reference_doctype": "Warehouse",
			"reference_document": "Finished Goods - CFC",
			"dimension_type": "Interior",
		},
	)
	orig_wh = {k: getattr(wh_dim, k) for k in ("item_length", "item_width", "item_height")}
	wh_dim.update({"item_length": 2.0, "item_width": 2.0, "item_height": 1.5})
	wh_dim.save()

	item_dim = frappe.get_doc(
		"Physical Dimension",
		{
			"reference_doctype": "Item",
			"reference_document": "Bilberry",
			"dimension_type": "Exterior",
			"item_uom": "Pound",
		},
	)
	orig_item = {k: getattr(item_dim, k) for k in ("item_length", "item_width", "item_height")}
	item_dim.update({"item_length": 1.0, "item_width": 1.0, "item_height": 1.0})
	item_dim.save()

	rate = (
		frappe.db.get_value("Item Price", {"item_code": "Bilberry", "buying": 1}, "price_list_rate")
		or 1.0
	)
	submitted_se = None
	draft_se = None

	try:
		se4 = frappe.new_doc("Stock Entry")
		se4.company = "Chelsea Fruit Co"
		se4.stock_entry_type = "Material Receipt"
		se4.append(
			"items",
			{"item_code": "Bilberry", "t_warehouse": "Finished Goods - CFC", "qty": 4, "basic_rate": rate},
		)
		se4.save()
		se4.submit()
		submitted_se = se4.name

		se5 = frappe.new_doc("Stock Entry")
		se5.company = "Chelsea Fruit Co"
		se5.stock_entry_type = "Material Receipt"
		se5.append(
			"items",
			{"item_code": "Bilberry", "t_warehouse": "Finished Goods - CFC", "qty": 5, "basic_rate": rate},
		)
		se5.save()
		draft_se = se5.name
		with pytest.raises(frappe.ValidationError) as exc_info:
			se5.submit()
		assert "Cartonization" in str(exc_info.value)

	finally:
		if submitted_se:
			frappe.get_doc("Stock Entry", submitted_se).cancel()
		if draft_se:
			leftover = frappe.get_doc("Stock Entry", draft_se)
			if leftover.docstatus == 1:
				leftover.cancel()
			else:
				frappe.delete_doc("Stock Entry", draft_se, force=True)

		wh_dim.update(orig_wh)
		wh_dim.save()
		item_dim.update(orig_item)
		item_dim.save()
		disable_cfc_cartonization()


@pytest.mark.order(100)
def test_resolve_item_physical_dimension_exact_pound():
	row = resolve_item_physical_dimension("Bilberry", "Exterior", "Pound")
	assert row.item_uom == "Pound"


@pytest.mark.order(101)
def test_resolve_item_physical_dimension_exact_box():
	row = resolve_item_physical_dimension("Bilberry", "Exterior", "Box")
	assert row.item_uom == "Box"
	assert (
		float(row.item_length) * float(row.item_width) > BILBERRY["item_length"] * BILBERRY["item_width"]
	)


@pytest.mark.order(102)
def test_resolve_item_physical_dimension_defaults_to_stock_uom_row():
	row = resolve_item_physical_dimension("Bilberry", "Exterior", None)
	assert row.item_uom == "Pound"


@pytest.mark.order(103)
def test_resolve_item_physical_dimension_returns_none_when_no_record():
	assert resolve_item_physical_dimension("Pie Box", "Exterior") is None


@pytest.mark.order(104)
def test_convert_stock_to_physical_dimension_units_same_as_stock():
	assert convert_stock_qty_to_physical_dimension_units(4.0, "Pound", "Bilberry") == 4.0


@pytest.mark.order(105)
def test_convert_stock_to_physical_dimension_units_boxes_from_bilberry_stock():
	assert convert_stock_qty_to_physical_dimension_units(24.0, "Box", "Bilberry") == pytest.approx(
		2.0
	)


@pytest.mark.order(106)
def test_convert_stock_to_physical_dimension_units_handles_none_pd_uom():
	assert convert_stock_qty_to_physical_dimension_units(8.0, None, "Bilberry") == 8.0


@pytest.mark.order(110)
def test_run_cartonization_explicit_pound_uom_matches_pound_physical_dimension_row():
	configure_cfc_cartonization("2D Floor", "Error")

	try:
		doc = make_doc([{"item_code": "Bilberry", "qty": 3, "uom": "Pound", "stock_uom": "Pound"}])
		run_cartonization(doc)
	finally:
		disable_cfc_cartonization()


@pytest.mark.order(111)
def test_run_cartonization_box_line_uses_box_exterior_physical_dimension_row():
	configure_cfc_cartonization("2D Floor", "Error")

	try:
		doc = make_doc(
			[
				{
					"item_code": "Bilberry",
					"qty": 1,
					"uom": "Box",
					"stock_uom": "Pound",
					"conversion_factor": 12,
					"transfer_qty": 12,
				}
			]
		)
		run_cartonization(doc)
	finally:
		disable_cfc_cartonization()


@pytest.mark.order(112)
def test_run_cartonization_box_line_overflow_raises():
	configure_cfc_cartonization("2D Floor", "Error")

	try:
		doc = make_doc(
			[
				{
					"item_code": "Bilberry",
					"qty": 5,
					"uom": "Box",
					"stock_uom": "Pound",
					"conversion_factor": 12,
					"transfer_qty": 60,
				}
			]
		)
		with pytest.raises(frappe.ValidationError) as exc_info:
			run_cartonization(doc)
		assert "Cartonization" in str(exc_info.value)
	finally:
		disable_cfc_cartonization()


@pytest.mark.order(113)
def test_run_cartonization_falls_back_to_box_physical_dimension_when_stock_row_missing():
	configure_cfc_cartonization("2D Floor", "Error")

	try:
		doc = make_doc(
			[{"item_code": "Solo Case Berry", "qty": 12, "uom": "Pound", "stock_uom": "Pound"}]
		)
		run_cartonization(doc)
	finally:
		disable_cfc_cartonization()


@pytest.mark.order(120)
def test_solve_cartonization_assigns_bilberry_to_chelsea_fruit_storage_warehouse_bin():
	"""Multi-bin solver uses Interior Physical Dimensions for Chelsea Fruit Co storage bins."""

	from inventory_tools.cartonization import solve_cartonization

	out = solve_cartonization(
		[
			{
				"item_code": "Bilberry",
				"qty": 2,
				"uom": "Pound",
				"stock_uom": "Pound",
				"name": "manual-packing-line-001",
			}
		],
		container_doctypes=["Warehouse"],
		settings={"mode": "3D Volumetric"},
		reference_document_filters={"Warehouse": ["Fruit Storage 1 - CFC"]},
	)

	assert isinstance(out.bins, list)
	assert len(out.bins) >= 1

	first_bin = out.bins[0]
	container = getattr(first_bin, "container", None) or first_bin.get("container")
	assert container
	assert container.get("doctype") == "Warehouse"
	assert container.get("name") == "Fruit Storage 1 - CFC"

	items_block = first_bin["items"] if isinstance(first_bin, dict) else first_bin.get("items", [])
	written_row = False
	for row in items_block:
		payload = dict(row) if hasattr(row, "keys") else row
		if payload.get("row_name") == "manual-packing-line-001":
			written_row = True
			assert payload.get("item_code") == "Bilberry"
	assert written_row
