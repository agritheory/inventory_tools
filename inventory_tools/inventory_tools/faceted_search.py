import json
from time import localtime

import frappe
from erpnext.e_commerce.api import *
from frappe.utils.data import flt, getdate


@frappe.whitelist(allow_guest=True)
def show_faceted_search_components(doctype="Item", filters=None):
	attributes = frappe.get_all(
		"Specification Attribute",
		{"applied_on": doctype},
		["component", "attribute_name", "numeric_values", "date_values", "name AS attribute_id"],
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
		elif attribute.date_values and values:
			# TODO: convert from epoch
			_values = [localtime(int(v)) for v in values]
			_min, _max = min(_values), max(_values)
		else:
			attribute.values = values

	return attributes


class FacetedSearchQuery(ProductQuery):
	def query_items_with_attributes(self, attributes, start=0):
		item_codes = []

		attributes_in_use = {k: v for (k, v) in attributes.items() if v}
		for attribute, spec_and_values in attributes_in_use.items():
			spec = spec_and_values.get("attribute_id")
			values = spec_and_values.get("values")
			if not isinstance(values, list):
				values = [values]
			filters = None

			date_or_numeric = frappe.get_value(
				"Specification Attribute", spec, ["numeric_values", "date_values"]
			)
			if date_or_numeric[0] == 1:
				filters = [
					["attribute", "=", attribute],
					["value", ">=", flt(values[0])],
					["value", "<=", flt(values[-1])],
				]
			elif date_or_numeric[1] == 1:
				filters = [
					["attribute", "=", attribute],
					["value", ">=", getdate(values[0]) if values[0] else "1900-1-1"],
					["value", "<=", getdate(values[-1]) if values[-1] else "2100-12-31"],
				]
			else:
				filters = {
					"attribute": attribute,
					"value": ["in", values],
				}
			print(values, filters)
			item_code_list = frappe.get_all(
				"Specification Value", fields=["reference_name"], filters=filters, debug=True
			)
			item_codes.append({x.reference_name for x in item_code_list})
		if item_codes:
			item_codes = list(set.intersection(*item_codes))
			self.filters.append(["item_code", "in", item_codes])

		return self.query_items(start=start)


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


@frappe.whitelist()
def update_specification_attribute_values(doc, method=None):
	specifications = list(
		set(
			frappe.get_all(
				"Specification Attribute",
				fields=["parent"],
				filters={"applied_on": doc.doctype},
				pluck="parent",
			)
		)
	)
	if not specifications:
		return
	for spec in specifications:
		spec = frappe.get_doc("Specification", spec)
		if spec.applies_to(doc):
			spec.create_linked_values(doc)
