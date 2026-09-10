# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import flt

from inventory_tools.cartonization import get_available_interior_containers
from inventory_tools.inventory_tools.doctype.physical_dimension.physical_dimension import (
	allowed_physical_dimension_reference_doctypes,
)

TEMPLATE_DOCTYPE = "Shipment Parcel Template"
INTERIOR_UOM = "Centimeter"
CHELSEA_SETTINGS = "Chelsea Fruit Co"
FIXTURE_MAIL_ORDER_SHIPPER = "Ambrosia 12in Pie Shipper"


def shipper_template_name(label):
	return f"{label} {frappe.generate_hash(length=6)}"


def make_parcel_template(name, length=30.0, width=20.0, height=15.0, weight=5.0):
	template = frappe.new_doc(TEMPLATE_DOCTYPE)
	template.parcel_template_name = name
	template.length = length
	template.width = width
	template.height = height
	template.weight = weight
	template.insert(ignore_permissions=True)
	return template


def get_interior_pd(template_name):
	return frappe.db.get_value(
		"Physical Dimension",
		{
			"reference_doctype": TEMPLATE_DOCTYPE,
			"reference_document": template_name,
			"dimension_type": "Interior",
			"uom": INTERIOR_UOM,
		},
		["name", "item_length", "item_width", "item_height", "item_weight"],
		as_dict=True,
	)


def count_template_physical_dimensions(template_name):
	return frappe.db.count(
		"Physical Dimension",
		{
			"reference_doctype": TEMPLATE_DOCTYPE,
			"reference_document": template_name,
		},
	)


def physical_dimensions_for_template(template_name):
	return set(
		frappe.get_all(
			"Physical Dimension",
			filters={
				"reference_doctype": TEMPLATE_DOCTYPE,
				"reference_document": template_name,
			},
			pluck="name",
		)
	)


def parcel_shipper_containers():
	return {
		container.reference_document
		for container in get_available_interior_containers(["Shipment Parcel Template"])
	}


def capture_cfc_sync_setting():
	return frappe.db.get_value(
		"Inventory Tools Settings",
		CHELSEA_SETTINGS,
		"sync_parcel_template_physical_dimension",
	)


def set_cfc_sync_setting(enabled):
	frappe.db.set_value(
		"Inventory Tools Settings",
		CHELSEA_SETTINGS,
		"sync_parcel_template_physical_dimension",
		1 if enabled else 0,
		update_modified=False,
	)


def restore_cfc_sync_setting(value):
	frappe.db.set_value(
		"Inventory Tools Settings",
		CHELSEA_SETTINGS,
		"sync_parcel_template_physical_dimension",
		value or 0,
		update_modified=False,
	)


def capture_all_sync_settings():
	return {
		name: frappe.db.get_value(
			"Inventory Tools Settings",
			name,
			"sync_parcel_template_physical_dimension",
		)
		for name in frappe.get_all("Inventory Tools Settings", pluck="name")
	}


def disable_all_sync_settings():
	for name in frappe.get_all("Inventory Tools Settings", pluck="name"):
		frappe.db.set_value(
			"Inventory Tools Settings",
			name,
			"sync_parcel_template_physical_dimension",
			0,
			update_modified=False,
		)


def restore_all_sync_settings(snapshot):
	for name, value in snapshot.items():
		frappe.db.set_value(
			"Inventory Tools Settings",
			name,
			"sync_parcel_template_physical_dimension",
			value or 0,
			update_modified=False,
		)


@pytest.mark.order(136)
def test_ambrosia_mail_order_shipper_syncs_interior_physical_dimension():
	"""
	Ambrosia Pie Company adds a mail-order pie shipper. Chelsea Fruit Co keeps parcel-template
	sync enabled, so saving the template creates one Interior Physical Dimension (cm, max load).
	"""
	previous_sync = capture_cfc_sync_setting()
	template_name = shipper_template_name("Ambrosia 12in Pie Shipper")
	try:
		set_cfc_sync_setting(True)
		existing_dimensions = physical_dimensions_for_template(template_name)

		make_parcel_template(template_name, length=40.0, width=25.0, height=18.0, weight=12.5)

		new_dimensions = physical_dimensions_for_template(template_name) - existing_dimensions
		assert len(new_dimensions) == 1

		interior = get_interior_pd(template_name)
		assert interior
		assert flt(interior.item_length) == flt(40.0)
		assert flt(interior.item_width) == flt(25.0)
		assert flt(interior.item_height) == flt(18.0)
		assert flt(interior.item_weight) == flt(12.5)
	finally:
		restore_cfc_sync_setting(previous_sync)


@pytest.mark.order(137)
def test_ambrosia_deep_dish_shipper_update_keeps_exterior_physical_dimension():
	"""
	Ambrosia deep-dish shippers carry a separate Exterior record for outer carton size. When the
	usable cavity on the template changes, Interior sync updates; Exterior stays as recorded.
	"""
	previous_sync = capture_cfc_sync_setting()
	template_name = shipper_template_name("Ambrosia Deep Dish Shipper")
	exterior_name = None
	try:
		set_cfc_sync_setting(True)
		make_parcel_template(template_name, length=30.0, width=20.0, height=10.0, weight=5.0)

		exterior = frappe.new_doc("Physical Dimension")
		exterior.reference_doctype = TEMPLATE_DOCTYPE
		exterior.reference_document = template_name
		exterior.dimension_type = "Exterior"
		exterior.uom = INTERIOR_UOM
		exterior.item_length = 32.0
		exterior.item_width = 22.0
		exterior.item_height = 12.0
		exterior.item_weight = 6.0
		exterior.insert(ignore_permissions=True)
		exterior_name = exterior.name

		assert count_template_physical_dimensions(template_name) == 2

		template = frappe.get_doc(TEMPLATE_DOCTYPE, template_name)
		template.length = 35.0
		template.width = 24.0
		template.height = 14.0
		template.weight = 8.0
		template.save()

		assert count_template_physical_dimensions(template_name) == 2

		interior = get_interior_pd(template_name)
		assert flt(interior.item_length) == flt(35.0)
		assert flt(interior.item_width) == flt(24.0)
		assert flt(interior.item_height) == flt(14.0)
		assert flt(interior.item_weight) == flt(8.0)

		exterior_after = frappe.get_doc("Physical Dimension", exterior_name)
		assert flt(exterior_after.item_length) == flt(32.0)
		assert flt(exterior_after.item_width) == flt(22.0)
		assert flt(exterior_after.item_height) == flt(12.0)
		assert flt(exterior_after.item_weight) == flt(6.0)
	finally:
		restore_cfc_sync_setting(previous_sync)


@pytest.mark.order(138)
def test_chelsea_disabling_sync_leaves_shipper_without_physical_dimension():
	"""
	Chelsea Fruit Co turns off parcel-template sync. A new Ambrosia shipper template saves without
	creating any Physical Dimension rows.
	"""
	sync_snapshot = capture_all_sync_settings()
	template_name = shipper_template_name("Ambrosia Trial Shipper")
	try:
		disable_all_sync_settings()
		existing_dimensions = physical_dimensions_for_template(template_name)

		make_parcel_template(template_name)

		assert physical_dimensions_for_template(template_name) == existing_dimensions
		assert count_template_physical_dimensions(template_name) == 0
	finally:
		restore_all_sync_settings(sync_snapshot)


@pytest.mark.order(139)
def test_allowed_reference_doctypes_includes_shipment_parcel_template():
	allowed = allowed_physical_dimension_reference_doctypes()
	assert TEMPLATE_DOCTYPE in allowed


@pytest.mark.order(140)
def test_manual_exterior_on_wholesale_shipper_has_no_item_uom():
	"""
	With sync off, ops can still record an optional Exterior Physical Dimension on a shipper
	template. Non-Item references clear Item UOM on save.
	"""
	sync_snapshot = capture_all_sync_settings()
	template_name = shipper_template_name("Ambrosia Wholesale Shipper")
	try:
		disable_all_sync_settings()
		make_parcel_template(template_name)

		exterior = frappe.new_doc("Physical Dimension")
		exterior.reference_doctype = TEMPLATE_DOCTYPE
		exterior.reference_document = template_name
		exterior.dimension_type = "Exterior"
		exterior.uom = INTERIOR_UOM
		exterior.item_length = 31.0
		exterior.item_width = 21.0
		exterior.item_height = 11.0
		exterior.item_weight = 4.0
		exterior.insert(ignore_permissions=True)

		saved = frappe.get_doc("Physical Dimension", exterior.name)
		assert not saved.item_uom
	finally:
		restore_all_sync_settings(sync_snapshot)


@pytest.mark.order(141)
def test_synced_shipper_interior_is_available_to_cartonization():
	"""
	Cartonization reads Interior Physical Dimensions on Shipment Parcel Template containers.
	Fixture shippers from before_test and newly synced templates both appear in the container list.
	"""
	previous_sync = capture_cfc_sync_setting()
	template_name = shipper_template_name("Ambrosia Mail Order Shipper")
	try:
		set_cfc_sync_setting(True)
		existing_shippers = parcel_shipper_containers()
		assert FIXTURE_MAIL_ORDER_SHIPPER in existing_shippers

		make_parcel_template(template_name, length=38.1, width=38.1, height=30.5, weight=11.0)

		updated_shippers = parcel_shipper_containers()
		assert template_name in updated_shippers - existing_shippers

		matching = [
			container
			for container in get_available_interior_containers(["Shipment Parcel Template"])
			if container.reference_document == template_name
		]
		assert len(matching) == 1
		assert flt(matching[0].item_length) == flt(38.1)
		assert flt(matching[0].item_width) == flt(38.1)
		assert flt(matching[0].item_height) == flt(30.5)
		assert flt(matching[0].item_weight) == flt(11.0)
		assert matching[0].uom == INTERIOR_UOM
	finally:
		restore_cfc_sync_setting(previous_sync)
