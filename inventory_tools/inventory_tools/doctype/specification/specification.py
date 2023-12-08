# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.core.doctype.doctype.doctype import no_value_fields, table_fields
from frappe.model.document import Document


class Specification(Document):
	def validate(self):
		self.title = f"{self.dt}"
		if self.apply_on:
			self.title += f" - {self.apply_on}"

		self.create_linked_values(frappe.get_doc(self.dt, self.apply_on))

	def create_linked_values(self, doc, extra_attributes=None):
		if not extra_attributes:
			extra_attributes = {}

		for at in self.attributes:
			if at.field:
				existing_attribute_value = frappe.db.get_value(
					"Specification Value",
					{
						"reference_doctype": at.applied_on,
						"reference_name": doc.name,
						"attribute": at.attribute_name,
					},
				)
				if existing_attribute_value:
					av = frappe.get_doc("Specification Value", existing_attribute_value)
				else:
					av = frappe.new_doc("Specification Value")
					av.reference_doctype = at.applied_on
					av.reference_name = doc.name
					av.attribute = at.attribute_name
				av.value = frappe.get_value(av.reference_doctype, av.reference_name, at.field)
				av.save()
			if at.attribute_name in extra_attributes:
				if isinstance(extra_attributes[at.attribute_name], (str, int, float)):
					existing_attribute_value = frappe.db.get_value(
						"Specification Value",
						{
							"reference_doctype": at.applied_on,
							"reference_name": doc.name,
							"attribute": at.attribute_name,
						},
					)
					if existing_attribute_value:
						av = frappe.get_doc("Specification Value", existing_attribute_value)
					else:
						av = frappe.new_doc("Specification Value")
						av.reference_doctype = at.applied_on
						av.reference_name = doc.name
						av.attribute = at.attribute_name
					av.value = extra_attributes[at.attribute_name]
					av.save()
					continue

				for value in extra_attributes[at.attribute_name]:  # list, tuple or set / not dict
					existing_attribute_value = frappe.db.get_value(
						"Specification Value",
						{
							"reference_doctype": at.applied_on,
							"reference_name": doc.name,
							"attribute": at.attribute_name,
						},
					)
					if existing_attribute_value:
						av = frappe.get_doc("Specification Value", existing_attribute_value)
					else:
						av = frappe.new_doc("Specification Value")
						av.reference_doctype = at.applied_on
						av.reference_name = doc.name
						av.attribute = at.attribute_name
					av.value = value
					av.save()


@frappe.whitelist()
def get_data_fieldnames(doctype):
	meta = frappe.get_meta(doctype)
	return sorted(
		f.fieldname for f in meta.fields if f.fieldtype not in no_value_fields + table_fields
	)
