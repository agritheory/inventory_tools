# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import datetime

import frappe
from erpnext.manufacturing.doctype.workstation.workstation import Workstation
from frappe.desk.reportview import execute
from frappe.utils.data import comma_and, flt, get_time, time_diff_in_hours, getdate


def working_hour_spans(start_time, end_time):
	"""48-hour spans for one working-hour row.

	Intended to match HRMS Shift Assignment Tool
	(get_query_checking_overlapping_shift_timings): an end at or before its start
	is moved forward 24 hours. Each span is also repeated one day later. HRMS
	compares a single pair, which misses a morning row against a shift that
	crossed midnight (22:00–06:00 overlaps 05:00–07:00).
	"""
	start = datetime.datetime.combine(datetime.date.min, get_time(start_time))
	end = datetime.datetime.combine(datetime.date.min, get_time(end_time))
	if end <= start:
		end += datetime.timedelta(hours=24)
	day = datetime.timedelta(hours=24)
	return ((start, end), (start + day, end + day))


def working_hours_overlap(left, right) -> bool:
	for left_start, left_end in left:
		for right_start, right_end in right:
			if left_start < right_end and right_start < left_end:
				return True
	return False


class InventoryToolsWorkstation(Workstation):
	def validate_working_hours(self, row):
		"""
		HASH: 9771ed4c572510ec51586606f9d57ab6459717f1
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/workstation/workstation.py
		METHOD: validate_working_hours
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
		HASH: 1417f9f12fa4ebd221201664cedaf2195eab9082
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/workstation/workstation.py
		METHOD: set_total_working_hours
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
				if row.enabled:
					self.total_working_hours += row.hours

	def validate_overlap_for_operation_timings(self):
		"""
		HASH: 1417f9f12fa4ebd221201664cedaf2195eab9082
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/workstation/workstation.py
		METHOD: validate_overlap_for_operation_timings

		Intentionally diverges from that ERPNext query. Overlap uses the same
		48-hour clock as HRMS shift assignment; see working_hour_spans.
		Disabled rows are ignored, matching ERPNext.
		"""
		rows = [
			row for row in self.get("working_hours") if row.enabled and row.start_time and row.end_time
		]
		spans = [(row, working_hour_spans(row.start_time, row.end_time)) for row in rows]
		for row, row_spans in spans:
			overlapping = [
				other.idx
				for other, other_spans in spans
				if other is not row and working_hours_overlap(row_spans, other_spans)
			]
			if overlapping:
				frappe.msgprint(
					frappe._("Row #{0}: May overlap with row {1}").format(row.idx, comma_and(overlapping)),
				)

	def set_hour_rate(self):
		"""
		HASH: 9771ed4c572510ec51586606f9d57ab6459717f1
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/workstation/workstation.py
		METHOD: set_hour_rate
		"""
		if self.workstation_operating_cost:
			net_hour_rate = 0.0
			for row in self.workstation_operating_cost:
				if row.from_date and getdate(row.from_date) <= getdate() <= getdate(row.to_date or "2100-1-1"):
					net_hour_rate += row.qty
			self.hour_rate = net_hour_rate
		else:
			self.hour_rate = (
				flt(self.hour_rate_labour)
				+ flt(self.hour_rate_electricity)
				+ flt(self.hour_rate_consumable)
				+ flt(self.hour_rate_rent)
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
			default_row = (
				default_fields[0].name,
				f"{frappe._('(Default Workstation)')} {' - ' if field_values else ''}{field_values}",
			)
			workstation.insert(0, default_row)

	return workstation
