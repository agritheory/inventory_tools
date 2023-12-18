import json

import frappe
from erpnext.e_commerce.product_data_engine.filters import ProductFiltersBuilder
from erpnext.e_commerce.product_data_engine.query import ProductQuery
from erpnext.setup.doctype.item_group.item_group import get_child_groups_for_website
from frappe.utils import cint, flt


@frappe.whitelist(allow_guest=True)
def show_faceted_search_components(doctype="Item", filters=None):
	attributes = frappe.get_all(
		"Specification Attribute",
		{"applied_on": doctype},
		["component", "attribute_name", "numeric_values", "field"],
		order_by="idx ASC",
	)

	for attribute in attributes:
		values = list(
			set(
				frappe.get_all(
					"Specification Value",
					{"attribute": attribute.attribute_name, "reference_doctype": doctype},
					pluck="value",
				)
			)
		)
		if attribute.numeric_values and values:
			_values = [flt(v) for v in values]
			_min, _max = min(_values), max(_values)
			attribute.values = [_min, _max]
		else:
			attribute.values = values

	return attributes


class FacetedSearchQuery(ProductQuery):
	def query_items_with_attributes(self, attributes, start=0):
		item_codes = set()

		attributes_in_use = {k: v for (k, v) in attributes.items() if v}
		for attribute, values in attributes_in_use.items():
			if not isinstance(values, list):
				values = [values]

			item_code_list = frappe.get_all(
				"Specification Value",
				fields=["reference_name"],
				filters=[
					["attribute", "=", attribute],
					["value", "in", values],
				],
			)

			for item_code in item_code_list:
				item_codes.add(item_code.reference_name)

		if item_codes:
			self.filters.append(["item_code", "in", list(item_codes)])

		return self.query_items(start=start)


@frappe.whitelist()
def get_specification_items(doctype: str, attribute_name: str, attribute_values: list[str]):
	attribute_values = json.loads(attribute_values)
	return frappe.get_all(
		"Specification Value",
		filters=[
			["reference_doctype", "=", doctype],
			["attribute", "=", attribute_name],
			["value", ">", attribute_values[0]],
			["value", "<", attribute_values[1]],
		],
		pluck="reference_name",
	)


@frappe.whitelist(allow_guest=True)
def get_product_filter_data(query_args=None):
	if isinstance(query_args, str):
		query_args = json.loads(query_args)

	query_args = frappe._dict(query_args)
	if query_args:
		search = query_args.get("search")
		field_filters = query_args.get("field_filters", {})
		attribute_filters = query_args.get("attributes", {})
		start = cint(query_args.start) if query_args.get("start") else 0
		item_group = query_args.get("item_group")
		from_filters = query_args.get("from_filters")
	else:
		search, attribute_filters, item_group, from_filters = None, None, None, None
		field_filters = {}
		start = 0

	if from_filters:
		start = 0

	sub_categories = []
	if item_group:
		sub_categories = get_child_groups_for_website(item_group, immediate=True)

	engine = FacetedSearchQuery()

	try:
		result = engine.query(
			attribute_filters, field_filters, search_term=search, start=start, item_group=item_group
		)
	except Exception:
		frappe.log_error("Product query with filter failed")
		return {"exc": "Something went wrong!"}

	filters = {}
	discounts = result["discounts"]

	if discounts:
		filter_engine = ProductFiltersBuilder()
		filters["discount_filters"] = filter_engine.get_discount_filters(discounts)

	return {
		"items": result["items"] or [],
		"filters": filters,
		"settings": engine.settings,
		"sub_categories": sub_categories,
		"items_count": result["items_count"],
	}
