# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import datetime
import json
import time
from pytz import UnknownTimeZoneError, timezone

import frappe
from frappe.core.doctype.doctype.doctype import no_value_fields, table_fields
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.utils.data import flt, get_datetime

from erpnext.controllers.queries import get_fields


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
					av.value = doc.get(at.field)
				else:
					av = frappe.new_doc("Specification Value")
					av.reference_doctype = at.applied_on
					av.reference_name = doc.name
					av.specification = self.name
					av.attribute = at.attribute_name
					av.field = at.field
					av.value = doc.get(at.field)
				if at.date_values:
					av.value = convert_to_epoch(av.value)
				if av.value:
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
	tzname = time.tzname if isinstance(time.tzname, (int, str)) else time.tzname[0]

	try:
		tz = timezone(tzname)
	except UnknownTimeZoneError:
		# default to beginning of epoch
		return

	d = datetime.datetime.now(tz)  # or some other local date
	utc_offset = d.utcoffset()
	if utc_offset:
		utc_offset_seconds = utc_offset.total_seconds()
		offset_d = (
			get_datetime(date) - datetime.timedelta(hours=12, seconds=int(utc_offset_seconds))
		) - get_datetime("1970-01-01")
		return offset_d.total_seconds()
	return


def convert_from_epoch(date):
	system_settings = frappe.get_cached_doc("System Settings", "System Settings")
	d = datetime.datetime.utcfromtimestamp(int(flt(date)))
	utc_offset = d.utcoffset().total_seconds() if d.utcoffset() else 0
	return (d + datetime.timedelta(hours=12, seconds=int(utc_offset))).date()


@frappe.whitelist()
def get_data_fieldnames(doctype):
	meta = frappe.get_meta(doctype)
	return sorted(
		f.fieldname for f in meta.fields if f.fieldtype not in no_value_fields + table_fields
	)


def get_applicable_specification(doc):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	if doc.doctype != "Item":  # implement other doctypes later
		return
	applicable_specifications = []
	specification = frappe.qb.DocType("Specification")
	specification_attribute = frappe.qb.DocType("Specification Attribute")

	specification_candidates = (
		frappe.qb.from_(specification)
		.from_(specification_attribute)
		.select(specification.name, specification.dt, specification.apply_on)
		.where(
			(specification.name == specification_attribute.parent)
			& (specification_attribute.applied_on == doc.doctype)
		)
		.run(as_dict=True)
	)

	i = frappe.get_meta(doc.doctype)
	for s in specification_candidates:
		if not s.apply_on:
			applicable_specifications.append(s.name)
		else:
			fields = [h.fieldname for h in i.fields if h.options == s.dt]
			if any([doc.get(field) == s.apply_on for field in fields]):
				applicable_specifications.append(s.name)

	return applicable_specifications


"""
Should return a union of existing specification values and specification attributes where values are not present

"""


@frappe.whitelist()
def get_specification_values(reference_doctype, reference_name, specification=None):
	_r = []
	if not specification:
		specs = get_applicable_specification(frappe.get_doc(reference_doctype, reference_name))
	else:
		specs = [specification]
	for s in specs:
		spec = frappe.get_cached_doc("Specification", s)
		for row in spec.attributes:
			r = frappe.get_all(
				"Specification Value",
				filters={
					"reference_doctype": reference_doctype,
					"reference_name": reference_name,
					"attribute": row.attribute_name,
					"specification": spec.name,
				},
				fields=["name AS row_name", "attribute", "value", "field", "specification"],
				order_by="attribute ASC, value ASC",
			)
			if not r:
				_r.append(
					frappe._dict(
						{
							"row_name": None,
							"attribute": row.attribute_name,
							"value": None,
							"field": row.field,
							"specification": spec.name,
						}
					)
				)
			else:
				[_r.append(i) for i in r]

	return _r


@frappe.whitelist()
def create_specification_values(
	spec, specifications=None, reference_doctype=None, reference_name=None
):
	if isinstance(specifications, str):
		specifications = [frappe._dict(**s) for s in json.loads(specifications)]
	specification = frappe.get_doc("Specification", spec)
	specification_values = frappe._dict(
		{
			s.get("attribute"): s.get("value")
			for s in specifications
			if not s.get("field") and s.get("value")
		}
	)
	for row in specification.attributes:
		if not row.field and not specification_values.get(row.attribute_name):
			continue
		value = specification_values.get(row.attribute_name) or None
		if frappe.flags.in_test:
			_create_specification_values(specification, row, value)
		else:
			frappe.enqueue(
				_create_specification_values,
				specification=specification,
				attribute=row,
				value=value,
				queue="short",
			)


def _create_specification_values(specification, attribute, value):
	apply_on_filters = []
	if specification.apply_on:
		apply_on_filters.append([frappe.scrub(specification.dt), "=", specification.apply_on])
	applicable_documents = frappe.get_all(attribute.applied_on, filters=apply_on_filters)
	for doc in applicable_documents:
		if not value:
			value = frappe.get_value(attribute.applied_on, doc.name, attribute.field)
		if not value:
			continue
		values = frappe._dict(
			{
				"attribute": attribute.attribute_name,
				"field": attribute.field,
				"specification": specification.name,
				"reference_doctype": attribute.applied_on,
				"reference_name": doc.name,
				"value": value,
			}
		)
		if not frappe.get_all("Specification Value", filters=values):
			s = frappe.new_doc("Specification Value")
			s.update(values)
			s.save()


@frappe.whitelist()
def update_specification_values(reference_doctype, reference_name, spec=None, specifications=None):
	if isinstance(specifications, str):
		specifications = json.loads(specifications)
		specifications = [frappe._dict(**s) for s in specifications]
	# convert dates to epoch
	existing_values = get_specification_values(reference_doctype, reference_name)
	# print('existing_values', reference_name)
	# [print(existing_value) for existing_value in existing_values]
	for s in specifications:
		if not s.row_name and not s.value and not s.field:
			continue
		if existing_values:
			for row in existing_values:
				# print(row)
				if row.row_name and row.row_name == s.row_name and row.value != s.value:
					if not s.value:
						frappe.delete_doc("Specification Value", row.row_name)
						continue
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
			av.specification = s.specification
			if s.field:
				s.value = frappe.get_value(reference_doctype, reference_name, s.field)
			av.value = s.value
			# TODO:
			date_values = frappe.get_value(
				"Specification Attribute", {"parent": spec, "attribute_name": s.attribute}, ["date_values"]
			)
			if date_values:
				av.value = convert_to_epoch(av.value)
			if av.value:
				av.save()


@frappe.whitelist()
def get_apply_on_fields(doctype):
	Spec = DocType("Specification")
	SpecAttr = DocType("Specification Attribute")
	query = (
		frappe.qb.from_(Spec)
		.select(Spec.dt, Spec.apply_on)
		.inner_join(SpecAttr)
		.on(Spec.name == SpecAttr.parent)
		.where(Spec.enabled == 1)
	)
	if doctype != "Specification":
		query = query.where(SpecAttr.applied_on == doctype)
	return query.distinct().run(as_dict=True)


@frappe.whitelist()
# @frappe.readonly()
@frappe.validate_and_sanitize_search_inputs
def specification_query(doctype, txt, searchfield, start, page_len, filters):
	_filters = {}
	if filters.get("reference_doctype") != "Specification":
		doc = frappe.get_doc(filters.get("reference_doctype"), filters.get("reference_name"))
		_filters["name"] = ["in", get_applicable_specification(doc)]

	search_fields = get_fields("Specification")
	specifications = frappe.get_all(
		"Specification",
		filters=_filters,
		fields=search_fields,
		limit_start=start,
		limit_page_length=page_len,
		as_list=1,
	)
	return specifications
