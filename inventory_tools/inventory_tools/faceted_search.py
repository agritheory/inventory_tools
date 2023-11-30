import json

import frappe
from frappe.utils.data import flt


@frappe.whitelist(allow_guest=True)
def show_faceted_search_components(doctype="Item", filters=None):
	attributes = frappe.get_all(
		"Specification Attribute",
		{"applied_on": doctype},
		["component", "attribute_name", "numeric_values"],
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


# @frappe.whitelist()
# def update_or_create_search_attributes(doc, method=None) --> None:
# 	pass


# @frappe.whitelist(allow_guest=True)
# def get_product_list(search=None, start=0, limit=12, filters=None):
# 	data = get_product_data(search, start, limit)

# 	for item in data:
# 		set_product_info_for_website(item)

# 	return [get_item_for_list_in_html(r) for r in data]


# def get_product_data(search=None, start=0, limit=12):
# 	# limit = 12 because we show 12 items in the grid view
# 	# base query
# 	query = """
# 		SELECT
# 			web_item_name, item_name, item_code, brand, route,
# 			website_image, thumbnail, item_group,
# 			description, web_long_description as website_description,
# 			website_warehouse, ranking
# 		FROM `tabWebsite Item`
# 		WHERE published = 1
# 		"""

# 	# search term condition
# 	if search:
# 		query += """ and (item_name like %(search)s
# 				or web_item_name like %(search)s
# 				or brand like %(search)s
# 				or web_long_description like %(search)s)"""
# 		search = "%" + cstr(search) + "%"

# 	# order by
# 	query += """ ORDER BY ranking desc, modified desc limit {} offset {}""".format(
# 		cint(limit),
# 		cint(start),
# 	)

# 	return frappe.db.sql(query, {"search": search}, as_dict=1)  # nosemgrep
