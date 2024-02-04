# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import datetime
import json
import time

import frappe
from dateutil.relativedelta import relativedelta
from frappe.core.doctype.doctype.doctype import no_value_fields, table_fields
from frappe.model.document import Document
from frappe.utils.data import flt, get_datetime, getdate
from pytz import timezone


class Specification(Document):
	def validate(self):
		self.title = f"{self.dt}"
		if self.apply_on:
			self.title += f" - {self.apply_on}"

	def create_linked_values(self, doc, extra_attributes=None):
		for at in self.attributes:
			if at.field:
				existing_attribute_value = frappe.db.get_value(
					"Specification Value",
					{
						"reference_doctype": at.applied_on,
						"reference_name": doc.name,
						"attribute": at.attribute_name,
						"specification": self.name,
					},
				)
				if existing_attribute_value:
					av = frappe.get_doc("Specification Value", existing_attribute_value)
					av.value = frappe.get_value(av.reference_doctype, av.reference_name, at.field)
				else:
					av = frappe.new_doc("Specification Value")
					av.reference_doctype = at.applied_on
					av.reference_name = doc.name
					av.specification = self.name
					av.attribute = at.attribute_name
					av.field = at.field
				if at.date_values:
					av.value = convert_to_epoch(av.value)
				av.save()
			if extra_attributes and at.attribute_name in extra_attributes:
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
					if at.date_values:
						av.value = convert_to_epoch(av.value)
					av.save()
					continue

				if not extra_attributes:
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
					if at.date_values:
						av.value = convert_to_epoch(av.value)
					av.save()

	@property
	def applied_on_doctypes(self):
		return [r.applied_on for r in self.attributes]

	def applies_to(self, doc):
		if doc.doctype not in self.applied_on_doctypes:
			return
		for field in doc.meta.fields:
			if field.options == self.dt and not self.apply_on:
				return True
			if field.options == self.dt and doc.get(field.fieldname) == self.apply_on:
				return True


def convert_to_epoch(date):
	system_settings = frappe.get_cached_doc("System Settings", "System Settings")
	d = datetime.datetime.now(
		timezone(time.tzname if isinstance(time.tzname, (int, str)) else time.tzname[0])
	)  # or some other local date )
	utc_offset = d.utcoffset().total_seconds()
	return (
		(get_datetime(date) - datetime.timedelta(hours=12, seconds=int(utc_offset)))
		- get_datetime("1970-1-1")
	).total_seconds()


def convert_from_epoch(date):
	system_settings = frappe.get_cached_doc("System Settings", "System Settings")
	d = datetime.datetime.utcfromtimestamp(int(date))
	utc_offset = d.utcoffset().total_seconds() if d.utcoffset() else 0
	return (d + datetime.timedelta(hours=12, seconds=int(utc_offset))).date()


@frappe.whitelist()
def get_data_fieldnames(doctype):
	meta = frappe.get_meta(doctype)
	return sorted(
		f.fieldname for f in meta.fields if f.fieldtype not in no_value_fields + table_fields
	)


@frappe.whitelist()
def get_specification_values(reference_doctype, reference_name):
	r = frappe.get_all(
		"Specification Value",
		filters={"reference_doctype": reference_doctype, "reference_name": reference_name},
		fields=["name AS row_name", "attribute", "value", "field", "specification"],
		order_by="attribute ASC, value ASC",
	)
	for row in r:
		date_values = frappe.get_value(
			"Specification Attribute",
			{"parent": row.specification, "attribute_name": row.attribute},
			["date_values"],
		)
		if date_values:
			row.value = convert_from_epoch(row.value)
	return r


@frappe.whitelist()
def update_specification_values(reference_doctype, reference_name, spec, specifications):
	if isinstance(specifications, str):
		specifications = json.loads(specifications)
		specifications = [frappe._dict(**s) for s in specifications]
	# convert dates to epoch
	existing_values = get_specification_values(reference_doctype, reference_name)
	for s in specifications:
		for row in existing_values:
			if row.row_name and row.row_name == s.row_name and row.value != s.value:
				date_values = frappe.get_value(
					"Specification Attribute", {"parent": spec, "attribute_name": s.attribute}, ["date_values"]
				)
				if date_values:
					s.value = convert_to_epoch(s.value)
				frappe.set_value("Specification Value", s.row_name, "value", s.value)
		if not s.row_name:
			av = frappe.new_doc("Specification Value")
			av.reference_doctype = reference_doctype
			av.reference_name = reference_name
			av.attribute = s.attribute
			av.specification = spec
			av.value = s.value
			# TODO:
			date_values = frappe.get_value(
				"Specification Attribute", {"parent": spec, "attribute_name": s.attribute}, ["date_values"]
			)
			if date_values:
				av.value = convert_to_epoch(av.value)
			av.save()
