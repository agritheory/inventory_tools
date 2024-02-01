import json

import frappe


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_alternative_workstations(doctype, txt, searchfield, start, page_len, filters):
	operation = frappe.qb.DocType("Operation")
	alternative_workstations = frappe.qb.DocType("Alternative Workstations")
	operation_value = filters.get("operation")
	qb_data = (
		frappe.qb.from_(operation)
		.left_join(alternative_workstations)
		.on(operation.name == alternative_workstations.parent)
		.select(alternative_workstations.workstation)
		.where(operation.name == operation_value)
	)
	workstation = frappe.db.sql(qb_data)
	return workstation
