import frappe
from frappe.utils.data import flt


@frappe.whitelist()
def show_faceted_search_components(doctype="Item"):
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
