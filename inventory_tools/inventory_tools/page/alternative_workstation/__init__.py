# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.manufacturing.doctype.work_order.work_order import get_hour_rate
from frappe import _
from frappe.utils import flt

from inventory_tools.inventory_tools.overrides.workstation import (
	get_anchor_workstation,
	is_compatible_workstation,
	resolve_alternative_workstation_names,
	throw_incompatible_workstation,
)


@frappe.whitelist()
def get_workstation_availability(work_order, operation=None):
	"""
	Get workstation availability data for the workstation chart
	Works with existing ERPNext alternative workstation setup
	"""
	if not work_order:
		frappe.throw(_("Work Order is required"))

	work_order_doc = frappe.get_doc("Work Order", work_order)
	operations_data = []

	# Get operations from work order
	operations = work_order_doc.operations
	if operation:
		operations = [op for op in operations if op.name == operation]

	for op in operations:
		default_ws = get_anchor_workstation(op.operation, work_order_doc.bom_no)

		operation_data = {
			"operation": op.operation,
			"operation_name": op.operation,  # Keep for reference
			"idx": op.idx,
			"workstation": op.workstation,
			"default_workstation": default_ws,
			"is_bom_default": op.workstation == default_ws,
			"is_completed": operation_is_completed(work_order_doc.name, op),
			"planned_start_time": op.planned_start_time,
			"planned_end_time": op.planned_end_time,
			"availability": get_workstation_availability_status(op.workstation, op.planned_start_time),
			"next_available": get_next_available_time(op.workstation, op.planned_start_time),
			"capacity": get_workstation_capacity(op.workstation),
			"alternatives": get_alternative_workstations_from_operation(
				op.operation,
				work_order_doc.company,
				work_order_doc.bom_no,
				default_ws,
				op.planned_start_time,
				op.workstation,
			),
		}
		operations_data.append(operation_data)

	return operations_data


def operation_is_completed(work_order, operation_row):
	if operation_row.status == "Completed":
		return True
	return bool(
		frappe.db.exists(
			"Job Card",
			{"work_order": work_order, "operation": operation_row.operation, "docstatus": 1},
		)
	)


def get_alternative_workstations_from_operation(
	operation, company, bom_no, default_workstation, planned_start_time, current_workstation=None
):
	return [
		{
			"workstation": ws_name,
			"availability": get_workstation_availability_status(ws_name, planned_start_time),
			"next_available": get_next_available_time(ws_name, planned_start_time),
			"capacity": get_workstation_capacity(ws_name),
			"is_bom_default": ws_name == default_workstation,
		}
		for ws_name in resolve_alternative_workstation_names(
			operation, company, current_workstation, bom_no
		)
	]


def get_workstation_availability_status(workstation, planned_start_time):
	"""
	Check if workstation is available at the planned start time
	"""
	if not workstation or not planned_start_time:
		return "unavailable"

	try:
		# Convert string to datetime if needed
		if isinstance(planned_start_time, str):
			planned_start_time = frappe.utils.get_datetime(planned_start_time)

		# Check for overlapping work orders
		woo = frappe.qb.DocType("Work Order Operation")
		wo = frappe.qb.DocType("Work Order")

		overlapping_orders = (
			frappe.qb.from_(woo)
			.join(wo)
			.on(woo.parent == wo.name)
			.select(frappe.qb.functions.Count("*").as_("count"))
			.where(
				(woo.workstation == workstation)
				& (wo.status.not_in(["Completed", "Cancelled", "Stopped"]))
				& (wo.docstatus == 1)
				& (
					((woo.planned_start_time <= planned_start_time) & (woo.planned_end_time > planned_start_time))
					| (
						(woo.planned_start_time < planned_start_time) & (woo.planned_end_time >= planned_start_time)
					)
				)
			)
		).run(as_dict=True)

		if overlapping_orders and overlapping_orders[0].count > 0:
			return "busy"

		return "available"

	except Exception as e:
		frappe.log_error(f"Error checking workstation availability: {str(e)}")
		return "unavailable"


def get_next_available_time(workstation, planned_start_time):
	"""
	Get the next available time slot for the workstation
	"""
	if not workstation:
		return None

	try:
		if isinstance(planned_start_time, str):
			planned_start_time = frappe.utils.get_datetime(planned_start_time)

		woo = frappe.qb.DocType("Work Order Operation")
		wo = frappe.qb.DocType("Work Order")

		next_free_time = (
			frappe.qb.from_(woo)
			.join(wo)
			.on(woo.parent == wo.name)
			.select(frappe.qb.functions.Max(woo.planned_end_time).as_("next_free"))
			.where(
				(woo.workstation == workstation)
				& (wo.status.not_in(["Completed", "Cancelled", "Stopped"]))
				& (wo.docstatus == 1)
				& (woo.planned_end_time > planned_start_time)
			)
		).run(as_dict=True)

		if next_free_time and next_free_time[0].next_free:
			return next_free_time[0].next_free

		return planned_start_time

	except Exception as e:
		frappe.log_error(f"Error getting next available time: {str(e)}")
		return planned_start_time


def get_workstation_capacity(workstation):
	"""
	Get workstation capacity per hour
	"""
	if not workstation:
		return 1

	try:
		workstation_doc = frappe.get_doc("Workstation", workstation)
		return workstation_doc.hour_rate_consumable or workstation_doc.hour_rate_labour or 1
	except Exception as e:
		frappe.log_error(f"Error getting workstation capacity: {str(e)}")
		return 1


@frappe.whitelist()
def assign_workstation(work_order, operation, workstation):
	"""
	Assign a workstation to an operation in the work order
	"""
	if not all([work_order, operation, workstation]):
		frappe.throw(_("Work Order, Operation, and Workstation are required"))

	work_order_doc = frappe.get_doc("Work Order", work_order)
	frappe.has_permission("Work Order", "write", doc=work_order_doc, throw=True)

	operation_row = next((op for op in work_order_doc.operations if op.operation == operation), None)
	if not operation_row:
		frappe.throw(_("Operation {0} not found in Work Order {1}").format(operation, work_order))

	if operation_is_completed(work_order_doc.name, operation_row):
		frappe.throw(
			_(
				"Operation {0} is already completed on Work Order {1}; its workstation can't be changed."
			).format(operation, work_order)
		)

	if not is_compatible_workstation(operation, workstation, work_order_doc.bom_no):
		throw_incompatible_workstation(workstation, operation)

	operation_row.workstation = workstation
	recalculate_operation_times(operation_row, workstation)

	sync_job_card_workstations(work_order, operation, workstation)
	work_order_doc.calculate_operating_cost()
	work_order_doc.flags.ignore_validate_update_after_submit = True
	work_order_doc.save(ignore_permissions=True)

	return {
		"message": _("Workstation {0} assigned to operation {1}").format(workstation, operation),
		"status": "success",
	}


def sync_job_card_workstations(work_order, operation, workstation):
	"""Only draft Job Cards follow the reassignment; submitted ones record where the work happened."""
	for jc_name in frappe.get_all(
		"Job Card",
		filters={"work_order": work_order, "operation": operation, "docstatus": 0},
		pluck="name",
	):
		jc = frappe.get_doc("Job Card", jc_name)
		if jc.workstation == workstation:
			continue
		jc.workstation = workstation
		jc.save(ignore_permissions=True)


def recalculate_operation_times(operation_row, workstation):
	"""
	Recalculate operation times based on the new workstation
	"""
	try:
		operation_row.hour_rate = flt(get_hour_rate(workstation))

		if operation_row.planned_start_time:
			next_available = get_next_available_time(workstation, operation_row.planned_start_time)

			if next_available and next_available > operation_row.planned_start_time:
				if operation_row.planned_end_time and operation_row.planned_start_time:
					duration = operation_row.planned_end_time - operation_row.planned_start_time
					operation_row.planned_start_time = next_available
					operation_row.planned_end_time = next_available + duration
				else:
					operation_row.planned_start_time = next_available

	except Exception as e:
		frappe.log_error(f"Error recalculating operation times: {str(e)}")
