# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import datetime

import frappe
from erpnext.manufacturing.doctype.workstation.workstation import Workstation
from frappe.desk.reportview import execute
from frappe.utils.data import comma_and, flt, get_time, time_diff_in_hours


class InventoryToolsWorkstation(Workstation):
	def validate_working_hours(self, row):
		"""
		HASH: 3b4d39766f78492bd2ba92dc6c6c5b91263d3e6d
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/workstation/workstation.py
		METHOD: update_operation_status
		"""
		if not (row.start_time and row.end_time):
			frappe.throw(frappe._("Row #{0}: Start Time and End Time are required").format(row.idx))

		if get_time(row.start_time) >= get_time(row.end_time):
			frappe.msgprint(
				frappe._("Row #{0}: End Time of {1} will be interpreted as occurring on the next day").format(
					row.idx, row.end_time
				)
			)

	def set_total_working_hours(self):
		"""
		HASH: 3b4d39766f78492bd2ba92dc6c6c5b91263d3e6d
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/workstation/workstation.py
		METHOD: update_operation_status
		"""
		self.total_working_hours = 0.0
		for row in self.working_hours:
			self.validate_working_hours(row)

			if row.start_time and row.end_time:
				if get_time(row.start_time) >= get_time(row.end_time):
					end_time = datetime.datetime.combine(
						datetime.date.today(), get_time(row.end_time)
					) + datetime.timedelta(hours=24)
					start_time = datetime.datetime.combine(datetime.date.today(), get_time(row.start_time))
					row.hours = flt(time_diff_in_hours(end_time, start_time), row.precision("hours"))
				else:
					row.hours = flt(time_diff_in_hours(row.end_time, row.start_time), row.precision("hours"))
				self.total_working_hours += row.hours

	def validate_overlap_for_operation_timings(self):
		"""
		HASH: 3b4d39766f78492bd2ba92dc6c6c5b91263d3e6d
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/workstation/workstation.py
		METHOD: update_operation_status
		"""
		for d in self.get("working_hours"):
			existing = frappe.db.sql_list(
				"""select idx from `tabWorkstation Working Hour`
				where parent = %s and name != %s
					and (
						(start_time between %s and %s) or
						(end_time between %s and %s) or
						(%s between start_time and end_time))
				""",
				(self.name, d.name, d.start_time, d.end_time, d.start_time, d.end_time, d.start_time),
			)

			if existing:
				frappe.msgprint(
					frappe._("Row #{0}: May overlap with row {1}").format(d.idx, comma_and(existing)),
				)


"""
	This function fetches Workstation of the document operation.
	In Operation you can select multiple workstations in Alternative Workstation field.
	In the Work Order, Operation table, and Job Card, there exists an Operation field.
	When selecting an operation, this function is responsible for fetching the workstations
	both from the Alternative Workstation and the default workstation.

	Example : 	Operation : Cool Pie Op
		Default Workstation: Cooling Racks Station
		Alternative Workstation:
			`````````````````````````````````````````````````````
			:	Cooling Station	, Refrigerator Station ,		:
			:													:
			:													:
			``````````````````````````````````````````````````````
		In work order and job card when you select operation Cool Pie Op then you find below workstation in workstation field
			:	Cooling Station			:
			:	Refrigerator Station	:
			:	Cooling Racks Station	:
"""


@frappe.whitelist()
@frappe.read_only()
@frappe.validate_and_sanitize_search_inputs
def get_alternative_workstations(doctype, txt, searchfield, start, page_len, filters):
	company = filters.get("company") or frappe.defaults.get_defaults().get("company")
	setting_value = frappe.get_cached_value(
		"Inventory Tools Settings", company, "allow_alternative_workstations"
	)

	if setting_value == "Do Not Allow Alternative Workstations":
		filters.pop("operation", None)
		filters.pop("company", None)
		return execute(
			"Workstation",
			filters=filters,
			fields=[searchfield],
			limit_start=start,
			limit_page_length=page_len,
			as_list=True,
		)

	operation = filters.get("operation")
	if not operation:
		frappe.throw(frappe._("Please select an Operation first."))

	searchfields = list(reversed(frappe.get_meta(doctype).get_search_fields()))
	default_workstation_name = frappe.db.get_value("Operation", operation, "workstation")
	Workstation = frappe.qb.DocType("Workstation")

	if setting_value == "Allow Alternative Workstations Based on Workstation Type":
		if not default_workstation_name:
			frappe.throw(frappe._("Default workstation not found for the selected operation."))

		workstation_type = frappe.db.get_value(
			"Workstation", default_workstation_name, "workstation_type"
		)
		if not workstation_type:
			frappe.throw(frappe._("Workstation type not found for the default workstation."))

		query = (
			frappe.qb.from_(Workstation)
			.select(*[Workstation[field] for field in searchfields])
			.where(Workstation.workstation_type == workstation_type)
			.distinct()
		)

		if txt:
			query = query.where(Workstation.name.like(f"%{txt}%"))

		query = query.orderby(Workstation.name).limit(page_len).offset(start)
		workstation = list(query.run(as_dict=False))  # <-- convert to list

	else:
		Operation = frappe.qb.DocType("Operation")
		AlternativeWorkstation = frappe.qb.DocType("Alternative Workstation")

		query = (
			frappe.qb.from_(Workstation)
			.join(AlternativeWorkstation)
			.on(Workstation.name == AlternativeWorkstation.workstation)
			.join(Operation)
			.on(AlternativeWorkstation.parent == Operation.name)
			.select(*[Workstation[field] for field in searchfields])
			.where(AlternativeWorkstation.parent == operation)
			.distinct()
		)

		if txt:
			query = query.where(Workstation.name.like(f"%{txt}%"))

		workstation = list(query.run(as_dict=False))

	if default_workstation_name and default_workstation_name not in [row[0] for row in workstation]:
		default_fields = frappe.db.get_values(
			"Workstation", default_workstation_name, searchfields, as_dict=True
		)
		if default_fields:
			field_values = ", ".join([v for k, v in default_fields[0].items() if k != "name"])
			_default = (
				default_fields[0].name,
				f"{frappe._('(Default Workstation)')} {' - ' if field_values else ''}{field_values}",
			)
			workstation.insert(0, _default)

	return workstation
