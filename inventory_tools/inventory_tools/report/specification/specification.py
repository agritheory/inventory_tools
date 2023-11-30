# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

from itertools import groupby

import frappe


def execute(filters=None):
	specification = frappe.get_doc("Specification", filters.specification)
	return get_columns(filters, specification), get_data(filters, specification)


def get_data(filters, specification):
	doctypes = [row.applied_on for row in specification.attributes]
	attributes = [row.attribute_name for row in specification.attributes]
	fields = {row.attribute_name: row.field for row in specification.attributes if row.field}
	_data = frappe.get_all(
		"Specification Value",
		{"reference_doctype": ["in", doctypes], "attribute": ["in", attributes]},
		["reference_doctype", "reference_name", "attribute", "value", "name"],
		order_by="reference_name",
	)
	data = []
	for ref, d in groupby(_data, key=lambda x: x.get("reference_name")):
		_d = sorted(sorted(list(d), key=lambda x: x.get("value")), key=lambda x: x.get("attribute"))
		data.append(
			{
				"reference_name": frappe.bold(ref),
				"indent": 0,
			}
		)
		for __d in _d:
			if __d.attribute in fields:
				__d.field = fields[__d.attribute]
			__d.indent = 1
			data.append(__d)
	return data


def get_columns(filters, specification):
	return [
		{
			"label": f"{specification.dt} - {specification.apply_on}"
			if specification.apply_on
			else specification.dt,
			"fieldname": "reference_name",
			"fieldtype": "Link",
			"options": "Doctype",
			"width": "250px",
		},
		{
			"label": "DocType",
			"fieldname": "reference_doctype",
			"fieldtype": "Data",
			"width": "250px",
		},
		{
			"fieldname": "attribute",
			"fieldtype": "Data",
			"label": "Attribute",
			"width": "200px",
		},
		{
			"fieldname": "value",
			"label": "Value",
			"fieldtype": "Data",
			"width": "250px",
		},
		{"fieldname": "field", "fieldtype": "Data", "hidden": 1},
		{"fieldname": "name", "fieldtype": "Data", "hidden": 1},
	]


@frappe.whitelist()
def set_value(docname, value):
	frappe.set_value("Specification Value", docname, "value", value)
	frappe.msgprint("Updated", alert=True)
