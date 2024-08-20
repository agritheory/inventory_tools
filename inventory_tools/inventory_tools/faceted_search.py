# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import json
from time import localtime

import frappe
from webshop.webshop.api import get_product_filter_data as webshop_get_product_filter_data
from webshop.webshop.product_data_engine.filters import ProductFiltersBuilder
from webshop.webshop.doctype.override_doctype.item_group import get_child_groups_for_website
from frappe.utils.data import cint, flt, getdate

from inventory_tools.inventory_tools.doctype.specification.specification import convert_to_epoch
from inventory_tools.inventory_tools.faceted_search_query import FacetedSearchQuery


@frappe.whitelist(allow_guest=True)
def show_faceted_search_components(doctype="Item", filters=None):
	attributes = frappe.get_all(
		"Specification Attribute",
		{"applied_on": doctype},
		[
			"component",
			"attribute_name",
			"numeric_values",
			"date_values",
			"name AS attribute_id",
		],
		order_by="idx ASC",
	)
	components = {
		attribute.attribute_name: {**attribute, "values": set(), "visible": False}
		for attribute in attributes
	}

	for attribute in attributes:
		values = sorted(
			list(
				set(
					frappe.get_all(
						"Specification Value",
						{"attribute": attribute.attribute_name, "reference_doctype": doctype},
						pluck="value",
					)
				)
			),
			key=lambda x: x or "",
		)
		if attribute.numeric_values and values:
			_values = [flt(v) for v in values]
			_min, _max = min(_values), max(_values)
			attribute.values = [_min, _max]
		elif attribute.date_values and values:
			_values = [localtime(int(flt(v))) for v in values]
			_min, _max = min(_values), max(_values)
		elif attribute.component == "FacetedSearchColorPicker":
			values = [
				tuple(r.values())
				for r in frappe.get_all(
					"Color",
					[
						"name",
						"color",
						"image",
					],
					order_by="name",
				)
			]
		[components[attribute.attribute_name]["values"].add(value) for value in values]
	return components


@frappe.whitelist(allow_guest=True)
def get_product_filter_data(query_args=None):
	its = frappe.get_last_doc("Inventory Tools Settings")
	if not its.show_on_website:
		return webshop_get_product_filter_data(query_args)

	if isinstance(query_args, str):
		query_args = json.loads(query_args)

	query_args = frappe._dict(query_args)

	if query_args:
		search = query_args.get("search")
		field_filters = query_args.get("field_filters", {})
		attribute_filters = query_args.get("attributes", {})
		sort_order = query_args.get("sort_order") if query_args.get("sort_order") else ""
		start = cint(query_args.start) if query_args.get("start") else 0
		item_group = query_args.get("item_group")
		from_filters = query_args.get("from_filters")
	else:
		search, attribute_filters, item_group, from_filters = None, None, None, None
		field_filters = {}
		start = 0
		sort_order = ""

	if from_filters:
		start = 0

	sub_categories = []
	if item_group:
		sub_categories = get_child_groups_for_website(item_group, immediate=True)

	engine = FacetedSearchQuery()

	# try:
	result = engine.query(
		attribute_filters,
		field_filters,
		search_term=search,
		start=start,
		item_group=item_group,
		sort_order=sort_order,
	)
	# except Exception:
	# 	frappe.log_error("Product query with filter failed")
	# 	return {"exc": "Something went wrong!"}

	filters = {}
	discounts = result["discounts"]

	if discounts:
		filter_engine = ProductFiltersBuilder()
		filters["discount_filters"] = filter_engine.get_discount_filters(discounts)

	r = {
		"items": result["items"] or [],
		"filters": filters,
		"settings": engine.settings,
		"sub_categories": sub_categories,
		"items_count": result["items_count"],
	}
	return r


@frappe.whitelist()
def update_specification_attribute_values(doc, method=None):
	specifications = frappe.get_all(
		"Specification Attribute",
		fields=["parent"],
		filters={"applied_on": doc.doctype},
		pluck="parent",
		distinct=True,
	)
	if not specifications:
		return
	for spec in specifications:
		spec = frappe.get_doc("Specification", spec)
		if spec.applies_to(doc):
			spec.create_linked_values(doc)


@frappe.whitelist()
def get_specification_items(attributes):
	attributes = json.loads(attributes) if isinstance(attributes, str) else attributes
	specification_items = set()

	attributes_in_use = {k: v for (k, v) in attributes.items() if v}
	for attribute, spec_and_values in attributes_in_use.items():
		spec = spec_and_values.get("attribute_id")
		values = spec_and_values.get("values")
		if not values:
			continue
		if not isinstance(values, list):
			values = [values]
		filters = None

		date_or_numeric = frappe.get_value(
			"Specification Attribute", spec, ["numeric_values", "date_values"], as_dict=True
		)
		if date_or_numeric.numeric_values == 1:
			values[0], values[-1] = (
				flt(values[0]) if values[0] else None,
				flt(values[-1]) if values[-1] else None,
			)
			if values[0] and values[-1] and values[0] > values[-1]:
				values[0], values[-1] = values[-1], values[0]
			filters = [
				["attribute", "=", attribute],
			]
			if values[0]:
				filters.append(
					["value", ">=", flt(values[0])],
				)
			if values[-1]:
				filters.append(
					["value", "<=", flt(values[-1])],
				)

		elif date_or_numeric.date_values == 1:
			filters = [
				["attribute", "=", attribute],
				[
					"value",
					">=",
					convert_to_epoch(getdate(values[0])) if values[0] else convert_to_epoch(getdate("1900-1-1")),
				],
				[
					"value",
					"<=",
					convert_to_epoch(getdate(values[-1]))
					if values[-1]
					else convert_to_epoch(getdate("2100-12-31")),
				],
			]
		else:
			filters = {
				"attribute": attribute,
				"value": ["in", values],
			}
		item_codes = frappe.get_all(
			"Specification Value",
			filters=filters,
			pluck="reference_name",
		)
		specification_items.update(item_codes)

	return list(specification_items)
