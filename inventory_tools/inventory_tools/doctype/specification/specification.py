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


@frappe.whitelist()
def get_data_fieldnames(doctype):
	meta = frappe.get_meta(doctype)
	return sorted(
		f.fieldname for f in meta.fields if f.fieldtype not in no_value_fields + table_fields
	)
