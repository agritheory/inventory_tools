# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import datetime

import frappe
from erpnext.manufacturing.doctype.workstation.workstation import Workstation
from frappe.desk.reportview import execute
from frappe.utils import cint
from frappe.utils.data import comma_and, cstr, flt, get_time, time_diff_in_hours, getdate


def validate_workstation_warehouse(doc, method=None):
	if not doc.get("warehouse"):
		return
	wh = frappe.db.get_value("Warehouse", doc.warehouse, ["is_group", "disabled"], as_dict=True)
	if wh and cint(wh.is_group):
		frappe.throw(
			frappe._("Workstation Warehouse cannot be a group warehouse. Please select a leaf warehouse.")
		)
	if wh and cint(wh.disabled):
		frappe.throw(frappe._("Workstation Warehouse cannot be disabled."))


def validate_job_card_alternative_workstation(doc, method=None):
	"""A changed workstation must share the BOM (or Operation) default workstation's warehouse."""
	if doc.is_new() or not doc.operation or not doc.workstation:
		return
	if (
		get_allow_alternative_workstations_setting(doc.company)
		== "Do Not Allow Alternative Workstations"
	):
		return
	previous = doc.get_doc_before_save()
	if not previous or previous.workstation == doc.workstation:
		return
	if not is_compatible_workstation(doc.operation, doc.workstation, doc.bom_no):
		throw_incompatible_workstation(doc.workstation, doc.operation)


def throw_incompatible_workstation(workstation, operation):
	frappe.throw(
		frappe._(
			"Workstation {0} is not compatible with Operation {1}. Use a workstation with the same "
			"warehouse as the operation's default workstation, or one with no warehouse."
		).format(frappe.bold(workstation), frappe.bold(operation))
	)


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
		HASH: 9771ed4c572510ec51586606f9d57ab6459717f1
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
				self.total_working_hours += row.hours

	def validate_overlap_for_operation_timings(self):
		"""
		HASH: ba442c4feb47cdb3a6a3173bf604b3f2a13ffaa4
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/workstation/workstation.py
		METHOD: validate_overlap_for_operation_timings
		"""
		for d in self.get("working_hours"):
			wh = frappe.qb.DocType("Workstation Working Hour")
			existing = (
				frappe.qb.from_(wh)
				.select(wh.idx)
				.where(
					(wh.parent == self.name)
					& (wh.name != d.name)
					& (wh.start_time < d.end_time)
					& (wh.end_time > d.start_time)
				)
				.run(pluck=True)
			)

			if existing:
				frappe.msgprint(
					frappe._("Row #{0}: May overlap with row {1}").format(d.idx, comma_and(existing)),
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


def get_allow_alternative_workstations_setting(company):
	return frappe.get_cached_value(
		"Inventory Tools Settings", company, "allow_alternative_workstations"
	)


def get_anchor_workstation(operation_name, bom_no=None):
	"""The BOM's workstation for this operation, falling back to the Operation default."""
	if bom_no:
		bom_workstation = frappe.db.get_value(
			"BOM Operation",
			{"parent": bom_no, "parenttype": "BOM", "operation": operation_name},
			"workstation",
			order_by="idx asc",
		)
		if bom_workstation:
			return bom_workstation
	return frappe.db.get_value("Operation", operation_name, "workstation")


def get_workstation_warehouses(workstation_names):
	names = list({name for name in workstation_names if name})
	if not names:
		return {}
	return {
		row.name: cstr(row.warehouse).strip() or None
		for row in frappe.get_all(
			"Workstation", filters={"name": ("in", names)}, fields=["name", "warehouse"]
		)
	}


def warehouse_is_compatible(anchor_warehouse, candidate_warehouse):
	if not candidate_warehouse:
		return True
	return bool(anchor_warehouse) and candidate_warehouse == anchor_warehouse


def filter_compatible_workstations(operation_name, workstation_names, bom_no=None):
	"""Alternatives must share the anchor workstation's warehouse, or have none."""
	anchor = get_anchor_workstation(operation_name, bom_no)
	warehouses = get_workstation_warehouses([anchor, *workstation_names])
	anchor_warehouse = warehouses.get(anchor)
	return [
		name
		for name in workstation_names
		if name == anchor or warehouse_is_compatible(anchor_warehouse, warehouses.get(name))
	]


def is_compatible_workstation(operation_name, workstation_name, bom_no=None):
	if not workstation_name:
		return True
	return bool(filter_compatible_workstations(operation_name, [workstation_name], bom_no))


def warehouse_compatibility_clause(workstation_table, anchor_warehouse):
	blank = workstation_table.warehouse.isnull() | (workstation_table.warehouse == "")
	if anchor_warehouse:
		return blank | (workstation_table.warehouse == anchor_warehouse)
	return blank


def iter_operation_alternative_workstation_names(operation_doc):
	if hasattr(operation_doc, "alternative_workstations") and operation_doc.alternative_workstations:
		for row in operation_doc.alternative_workstations:
			if hasattr(row, "workstation") and row.workstation:
				yield row.workstation
	if hasattr(operation_doc, "alternative_workstation") and operation_doc.alternative_workstation:
		for alt_row in operation_doc.alternative_workstation:
			if hasattr(alt_row, "workstation") and alt_row.workstation:
				yield alt_row.workstation


def resolve_alternative_workstation_names(
	operation, company, current_workstation=None, bom_no=None
):
	setting_value = get_allow_alternative_workstations_setting(company)
	if setting_value == "Do Not Allow Alternative Workstations":
		return []

	default_workstation_name = frappe.db.get_value("Operation", operation, "workstation")
	anchor_workstation = get_anchor_workstation(operation, bom_no)

	if setting_value == "Allow Alternative Workstations Based on Workstation Type":
		if not default_workstation_name:
			return []
		workstation_type = frappe.db.get_value(
			"Workstation", default_workstation_name, "workstation_type"
		)
		if not workstation_type:
			return []
		candidates = frappe.get_all(
			"Workstation", filters={"workstation_type": workstation_type}, pluck="name"
		)
	else:
		operation_doc = frappe.get_doc("Operation", operation)
		candidates = [
			anchor_workstation,
			default_workstation_name,
			*iter_operation_alternative_workstation_names(operation_doc),
		]

	names = []
	for ws_name in candidates:
		if not ws_name or ws_name == current_workstation or ws_name in names:
			continue
		names.append(ws_name)

	return filter_compatible_workstations(operation, names, bom_no)


@frappe.whitelist()
@frappe.read_only()
@frappe.validate_and_sanitize_search_inputs
def get_alternative_workstations(doctype, txt, searchfield, start, page_len, filters):
	company = filters.get("company") or frappe.defaults.get_defaults().get("company")
	setting_value = get_allow_alternative_workstations_setting(company)

	bom_no = filters.pop("bom_no", None)
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
	anchor_workstation = get_anchor_workstation(operation, bom_no)
	anchor_wh = get_workstation_warehouses([anchor_workstation]).get(anchor_workstation)
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
			.where(warehouse_compatibility_clause(Workstation, anchor_wh))
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
			.where(warehouse_compatibility_clause(Workstation, anchor_wh))
			.distinct()
		)

		if txt:
			query = query.where(Workstation.name.like(f"%{txt}%"))

		workstation = list(query.run(as_dict=False))

	if anchor_workstation and anchor_workstation not in [row[0] for row in workstation]:
		default_fields = frappe.db.get_values(
			"Workstation", anchor_workstation, searchfields, as_dict=True
		)
		if default_fields:
			field_values = ", ".join([v for k, v in default_fields[0].items() if k != "name"])
			default_row = (
				default_fields[0].name,
				f"{frappe._('(Default Workstation)')} {' - ' if field_values else ''}{field_values}",
			)
			workstation.insert(0, default_row)

	return workstation
