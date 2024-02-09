import json
import frappe

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_alternative_workstations(doctype, txt, searchfield, start, page_len, filters):
	operation = filters.get('operation')
	operation_doc = frappe.qb.DocType("Operation")
	alternative_workstations = frappe.qb.DocType("Alternative Workstations")
	qb_data = (
		frappe.qb.from_(operation_doc)
		.left_join(alternative_workstations)
		.on(operation_doc.name == alternative_workstations.parent)
		.select(alternative_workstations.workstation)
		.where(operation_doc.name == operation)
	)
	workstation = frappe.db.sql(qb_data)
	default_workstation = frappe.db.get_value("Operation", operation, 'workstation')
	if workstation:
		workstation += ((default_workstation,),)
	else:
		workstation = ((default_workstation,),)
	return workstation