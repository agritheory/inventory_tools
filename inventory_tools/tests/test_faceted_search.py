# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest

from inventory_tools.tests.fixtures import attributes

# don't generate spec values in setup
# create overlapping spec (Item)

# test generation of values for

# spec_items = frappe.get_all("Item", {"item_group": "Baked Goods"})
# for spec_item in spec_items:
# 	if spec_item.name not in attributes:
# 		continue
# 	spec_item = frappe.get_doc("Item", spec_item)
# 	s.create_linked_values(spec_item, attributes[spec_item.name])


@pytest.mark.order(70)
def test_values_updated_on_item_save():
	# assert spec value doesn't exist
	frappe.flags.in_test = True
	values = frappe.get_all(
		"Specification Value", {"reference_doctype": "Item", "reference_name": "Double Plum Pie"}
	)
	assert values == []
	doc = frappe.get_doc("Item", "Double Plum Pie")
	doc.save()
	values = frappe.get_all(
		"Specification Value", {"reference_doctype": "Item", "reference_name": "Double Plum Pie"}
	)
	assert len(values) == 4
	doc.weight_per_unit = 12
	doc.save()
	values = frappe.get_all(
		"Specification Value",
		{"reference_doctype": "Item", "reference_name": "Double Plum Pie"},
	)
	assert len(values) == 4
	new_weight = frappe.get_all(
		"Specification Value",
		{"reference_doctype": "Item", "reference_name": "Double Plum Pie", "attribute": "Weight"},
		"value",
	)
	assert len(new_weight) == 1
	assert int(new_weight[0].value) == 12
	doc.weight_per_unit = 8
	doc.save()
	new_weight = frappe.get_all(
		"Specification Value",
		{"reference_doctype": "Item", "reference_name": "Double Plum Pie", "attribute": "Weight"},
		"value",
	)
	assert len(new_weight) == 1
	assert int(new_weight[0].value) == 8
	values = frappe.get_all(
		"Specification Value", {"reference_doctype": "Item", "reference_name": "Double Plum Pie"}
	)
	assert len(values) == 4
	# cleanup
	for value in values:
		frappe.delete_doc("Specification Value", value.name, force=True)


@pytest.mark.order(71)
def test_generate_values():
	frappe.flags.in_test = True
	doc = frappe.get_doc("Specification", "Items")
	assert len(doc.attributes) == 3
	frappe.call(
		"inventory_tools.inventory_tools.doctype.specification.specification.create_specification_values",
		**{
			"spec": doc.name,
			"specifications": [
				{
					"attribute": a.attribute_name,
					"field": a.field,
				}
				for a in doc.attributes
			],
		}
	)
	_len = len(frappe.get_all("Specification Value", {"specification": doc.name}))
	# total items x computed attributes
	assert _len == 126 * 2


@pytest.mark.order(72)
def test_generate_values_on_overlapping_items():
	frappe.flags.in_test = True
	doc = frappe.get_doc("Specification", "Baked Goods")
	assert len(doc.attributes) == 4
	assert len(frappe.get_all("Specification Value", {"specification": doc.name})) == 0
	frappe.call(
		"inventory_tools.inventory_tools.doctype.specification.specification.create_specification_values",
		**{
			"spec": doc.name,
			"specifications": [
				{
					"attribute": a.attribute_name,
					"field": a.field,
				}
				for a in doc.attributes
			],
		}
	)
	assert (
		len(frappe.get_all("Specification Value", {"specification": doc.name})) == 6 * 2
	)  # total items x computed attributes


@pytest.mark.order(73)
def test_manual_attribute_addition():
	for item, fixtures_values in attributes.items():
		_args = {
			"reference_doctype": "Item",
			"reference_name": item,
			"specification": "Items",
		}
		values = frappe.call(
			"inventory_tools.inventory_tools.doctype.specification.specification.get_specification_values",
			**_args
		)
		for attribute, manual_values in fixtures_values.items():
			if isinstance(manual_values, list):
				for v in manual_values:
					values.append({"row_name": "", "attribute": attribute, "value": v, "specification": "Items"})
			else:
				values.append(
					{
						"row_name": "",
						"attribute": attribute,
						"value": manual_values,
						"specification": "Items",
					}
				)
		# print(existing_values)
		args = {
			"spec": "Items",
			"specifications": frappe.as_json(values),
			"reference_doctype": "Item",
			"reference_name": item,
		}
		frappe.call(
			"inventory_tools.inventory_tools.doctype.specification.specification.update_specification_values",
			**args
		)
	assert (
		len(frappe.get_all("Specification Value", {"specification": "Items", "attribute": "Color"}))
		== 25
	)  # all colors in baked goods items from fixtures


@pytest.mark.order(74)
def test_delete_of_specification_value():
	frappe.flags.in_test = True
	_args = {
		"reference_doctype": "Item",
		"reference_name": "Ambrosia Pie",
		"specification": "Items",
	}
	values = frappe.call(
		"inventory_tools.inventory_tools.doctype.specification.specification.get_specification_values",
		**_args
	)
	colors = [v.value for v in values if v.attribute == "Color"]
	assert "Blue" in colors
	assert len(colors) == 2

	for v in values:
		if v.attribute == "Color" and v.value == "Blue":
			v.value = None

	args = {
		"spec": _args.get("specification"),
		"specifications": frappe.as_json(values),
		"reference_doctype": _args.get("reference_doctype"),
		"reference_name": _args.get("reference_name"),
	}
	frappe.call(
		"inventory_tools.inventory_tools.doctype.specification.specification.update_specification_values",
		**args
	)
	assert (
		len(
			frappe.get_all(
				"Specification Value",
				{
					"specification": "Items",
					"attribute": "Color",
					"reference_name": _args.get("reference_name"),
				},
			)
		)
		== 1
	)  # all colors in baked goods items from fixtures
