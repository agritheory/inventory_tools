import json
from time import localtime

import frappe
from erpnext.e_commerce.api import *
from frappe.utils.data import flt, getdate

from inventory_tools.inventory_tools.doctype.specification.specification import convert_to_epoch


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
			_values = [localtime(int(v)) for v in values]
			_min, _max = min(_values), max(_values)
		else:
			attribute.values = values

	return attributes


sort_order_lookup = {
	"Title A-Z": "item_name ASC, ranking DESC",
	"Title Z-A": "item_name DESC, ranking DESC",
	"Item Code A-Z": "item_code ASC, ranking DESC",
	"Item Code Z-A": "item_code DESC, ranking DESC",
}


class FacetedSearchQuery(ProductQuery):
	def query(
		self, attributes=None, fields=None, search_term=None, start=0, item_group=None, sort_order=""
	):
		print(attributes, fields, search_term, start, item_group, sort_order)
		# track if discounts included in field filters
		self.filter_with_discount = bool(fields.get("discount"))
		result, discount_list, website_item_groups, cart_items, count = [], [], [], [], 0

		if fields:
			self.build_fields_filters(fields)
		if item_group:
			self.build_item_group_filters(item_group)
		if search_term:
			self.build_search_filters(search_term)
		if self.settings.hide_variants:
			self.filters.append(["variant_of", "is", "not set"])

		print("query", sort_order)
		sort_order = sort_order_lookup.get(sort_order) if sort_order else "item_name ASC"

		# query results
		if attributes:
			result, count = self.query_items_with_attributes(attributes, start, sort_order=sort_order)
		else:
			result, count = self.query_items(start=start, sort_order=sort_order)

		# sort combined results by ranking
		result = sorted(result, key=lambda x: x.get("ranking"), reverse=True)

		if self.settings.enabled:
			cart_items = self.get_cart_items()

		result, discount_list = self.add_display_details(result, discount_list, cart_items)

		discounts = []
		if discount_list:
			discounts = [min(discount_list), max(discount_list)]

		result = self.filter_results_by_discount(fields, result)

		return {"items": result, "items_count": count, "discounts": discounts}

	def query_items(self, start=0, sort_order=""):
		print("query_items", sort_order)
		"""Build a query to fetch Website Items based on field filters."""
		# MySQL does not support offset without limit,
		# frappe does not accept two parameters for limit
		# https://dev.mysql.com/doc/refman/8.0/en/select.html#id4651989
		count_items = frappe.db.get_all(
			"Website Item",
			filters=self.filters,
			or_filters=self.or_filters,
			limit_page_length=184467440737095516,
			limit_start=start,  # get all items from this offset for total count ahead
			order_by=sort_order,
			# debug=True
		)
		count = len(count_items)

		# If discounts included, return all rows.
		# Slice after filtering rows with discount (See `filter_results_by_discount`).
		# Slicing before hand will miss discounted items on the 3rd or 4th page.
		# Discounts are fetched on computing Pricing Rules so we cannot query them directly.
		page_length = 184467440737095516 if self.filter_with_discount else self.page_length

		items = frappe.db.get_all(
			"Website Item",
			fields=self.fields,
			filters=self.filters,
			or_filters=self.or_filters,
			limit_page_length=page_length,
			limit_start=start,
			order_by=sort_order,
			# debug=True
		)

		return items, count

	def query_items_with_attributes(self, attributes, start=0, sort_order=""):
		item_codes = []

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
				"Specification Attribute", spec, ["numeric_values", "date_values"]
			)
			if date_or_numeric[0] == 1:

				if values[0] > values[-1]:
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

			elif date_or_numeric[1] == 1:
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
			item_code_list = frappe.get_all(
				"Specification Value",
				fields=["reference_name"],
				filters=filters,  # debug=True
			)
			item_codes.append({x.reference_name for x in item_code_list})

		if item_codes:
			item_codes = list(set.intersection(*item_codes))
			self.filters.append(["item_code", "in", item_codes])

		return self.query_items(start=start, sort_order=sort_order)


@frappe.whitelist(allow_guest=True)
def get_product_filter_data(query_args=None):
	if isinstance(query_args, str):
		query_args = json.loads(query_args)

	query_args = frappe._dict(query_args)

	if query_args:
		search = query_args.get("search")
		field_filters = query_args.get("field_filters", {})
		attribute_filters = query_args.get("attributes", {})
		sort_order = (
			query_args.get("sort_order").get("sort_order") if query_args.get("sort_order") else ""
		)
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
