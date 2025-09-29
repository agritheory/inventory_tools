# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _


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
		# Get the Operation master to fetch alternative workstations
		operation_master = frappe.get_doc("Operation", op.operation)

		operation_data = {
			"operation": op.operation,
			"operation_name": op.operation,  # Keep for reference
			"idx": op.idx,
			"workstation": op.workstation,
			"planned_start_time": op.planned_start_time,
			"planned_end_time": op.planned_end_time,
			"availability": get_workstation_availability_status(op.workstation, op.planned_start_time),
			"next_available": get_next_available_time(op.workstation, op.planned_start_time),
			"capacity": get_workstation_capacity(op.workstation),
			"alternatives": get_alternative_workstations_from_operation(
				operation_master, op.planned_start_time, op.workstation
			),
		}
		operations_data.append(operation_data)

	return operations_data


def get_alternative_workstations_from_operation(
	operation_doc, planned_start_time, current_workstation=None
):
	"""
	Get alternative workstations from Operation master document
	"""
	alternatives = []

	# Check if Operation has alternative workstations configured
	# In ERPNext, this could be in various formats - let's handle them

	# Method 1: Check for alternative_workstations field (if it exists as multiselect or similar)
	if hasattr(operation_doc, "alternative_workstations") and operation_doc.alternative_workstations:
		workstation_names = []

		# Handle different field types
		if isinstance(operation_doc.alternative_workstations, str):
			# Could be JSON string, comma-separated, or newline-separated
			import json

			try:
				# Try JSON first
				workstation_names = json.loads(operation_doc.alternative_workstations)
				if isinstance(workstation_names, str):
					workstation_names = [workstation_names]
			except (json.JSONDecodeError, TypeError):
				# Try comma or newline separation
				workstation_names = [
					name.strip()
					for name in operation_doc.alternative_workstations.replace("\n", ",").split(",")
					if name.strip()
				]
		elif isinstance(operation_doc.alternative_workstations, list):
			workstation_names = operation_doc.alternative_workstations

		for workstation_name in workstation_names:
			if not workstation_name:
				continue
			if current_workstation and workstation_name == current_workstation:
				continue  # 🚀 skip the primary
			if workstation_name and workstation_name != operation_doc.workstation:
				alternative_data = {
					"workstation": workstation_name.workstation,
					"availability": get_workstation_availability_status(workstation_name, planned_start_time),
					"next_available": get_next_available_time(workstation_name, planned_start_time),
					"capacity": get_workstation_capacity(workstation_name),
				}
				alternatives.append(alternative_data)

	# Method 2: Check if there's a child table for alternative workstations
	if hasattr(operation_doc, "alternative_workstation") and operation_doc.alternative_workstation:
		for alt_row in operation_doc.alternative_workstation:
			if hasattr(alt_row, "workstation") and alt_row.workstation:
				alternative_data = {
					"workstation": alt_row.workstation,
					"availability": get_workstation_availability_status(alt_row.workstation, planned_start_time),
					"next_available": get_next_available_time(alt_row.workstation, planned_start_time),
					"capacity": get_workstation_capacity(alt_row.workstation),
				}
				alternatives.append(alternative_data)

	return alternatives


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
		overlapping_orders = frappe.db.sql(
			"""
            SELECT COUNT(*) as count
            FROM `tabWork Order Operation` woo
            JOIN `tabWork Order` wo ON woo.parent = wo.name
            WHERE woo.workstation = %s
            AND wo.status NOT IN ('Completed', 'Cancelled', 'Stopped')
            AND wo.docstatus = 1
            AND (
                (woo.planned_start_time <= %s AND woo.planned_end_time > %s)
                OR (woo.planned_start_time < %s AND woo.planned_end_time >= %s)
            )
        """,
			(workstation, planned_start_time, planned_start_time, planned_start_time, planned_start_time),
			as_dict=True,
		)

		if overlapping_orders and overlapping_orders[0].count > 0:
			return "busy"

		# Check workstation working hours and holidays
		workstation_doc = frappe.get_doc("Workstation", workstation)
		if workstation_doc.holiday_list:
			from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday

			if is_holiday(workstation_doc.holiday_list, planned_start_time.date()):
				return "unavailable"

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

		# Find the earliest time when workstation is free
		next_free_time = frappe.db.sql(
			"""
            SELECT MAX(woo.planned_end_time) as next_free
            FROM `tabWork Order Operation` woo
            JOIN `tabWork Order` wo ON woo.parent = wo.name
            WHERE woo.workstation = %s
            AND wo.status NOT IN ('Completed', 'Cancelled', 'Stopped')
            AND wo.docstatus = 1
            AND woo.planned_end_time > %s
        """,
			(workstation, planned_start_time),
			as_dict=True,
		)

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

	try:
		# Get and update the work order
		work_order_doc = frappe.get_doc("Work Order", work_order)

		# Find and update the specific operation
		operation_found = False
		for op in work_order_doc.operations:
			if op.operation == operation:
				old_workstation = op.workstation
				op.workstation = workstation

				# Recalculate times based on new workstation if needed
				recalculate_operation_times(op, workstation)
				operation_found = True
				break

		if not operation_found:
			frappe.throw(_("Operation {0} not found in Work Order {1}").format(operation, work_order))

		# Save the work order
		work_order_doc.save(ignore_permissions=True)
		frappe.db.commit()
		work_order_doc.reload()

		# Log the change
		frappe.logger().info(
			f"Workstation changed from {old_workstation} to {workstation} for operation {operation} in work order {work_order}"
		)

		return {
			"message": _("Workstation {0} assigned to operation {1}").format(workstation, operation),
			"status": "success",
		}

	except Exception as e:
		frappe.log_error(f"Error assigning workstation: {str(e)}")
		frappe.throw(_("Failed to assign workstation: {0}").format(str(e)))


def recalculate_operation_times(operation_row, workstation):
	"""
	Recalculate operation times based on the new workstation
	"""
	try:
		workstation_doc = frappe.get_doc("Workstation", workstation)

		# Update hour rate if workstation has different rates
		if workstation_doc.hour_rate:
			operation_row.hour_rate = workstation_doc.hour_rate

		# Get next available time for the new workstation
		if operation_row.planned_start_time:
			next_available = get_next_available_time(workstation, operation_row.planned_start_time)

			if next_available and next_available > operation_row.planned_start_time:
				# Calculate duration to maintain operation time
				if operation_row.planned_end_time and operation_row.planned_start_time:
					duration = operation_row.planned_end_time - operation_row.planned_start_time
					operation_row.planned_start_time = next_available
					operation_row.planned_end_time = next_available + duration
				else:
					operation_row.planned_start_time = next_available

	except Exception as e:
		frappe.log_error(f"Error recalculating operation times: {str(e)}")
		# Continue without failing the entire operation


@frappe.whitelist()
def get_workstation_schedule(workstation, from_date=None, to_date=None):
	"""
	Get detailed schedule for a workstation for calendar/timeline view
	"""
	if not from_date:
		from_date = frappe.utils.today()
	if not to_date:
		to_date = frappe.utils.add_days(from_date, 30)

	try:
		schedule = frappe.db.sql(
			"""
            SELECT
                wo.name as work_order,
                woo.operation,
                woo.planned_start_time,
                woo.planned_end_time,
                wo.production_item,
                wo.qty,
                wo.status,
                woo.completed_qty,
                woo.process_loss_qty
            FROM `tabWork Order Operation` woo
            JOIN `tabWork Order` wo ON woo.parent = wo.name
            WHERE woo.workstation = %s
            AND DATE(woo.planned_start_time) BETWEEN %s AND %s
            AND wo.docstatus = 1
            AND wo.status NOT IN ('Cancelled')
            ORDER BY woo.planned_start_time
        """,
			(workstation, from_date, to_date),
			as_dict=True,
		)

		return schedule

	except Exception as e:
		frappe.log_error(f"Error getting workstation schedule: {str(e)}")
		return []
