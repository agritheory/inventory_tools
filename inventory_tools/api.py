import json

import frappe


@frappe.whitelist()
def get_alternative_workstations(operation):
	operation_doc = frappe.qb.DocType("Operation")
	alternative_workstations = frappe.qb.DocType("Alternative Workstations")
	qb_data = (
		frappe.qb.from_(operation_doc)
		.left_join(alternative_workstations)
		.on(operation_doc.name == alternative_workstations.parent)
		.select(alternative_workstations.workstation)
		.where(operation_doc.name == operation)
	)
	workstation = frappe.db.sql(qb_data, as_dict=1)
	return workstation


# set alternative workstation in job card
def set_alternative_workstations(self, method):
	if self.operation and self.is_new():
		workstations = get_alternative_workstations(self.operation)
		if not self.custom_alternative_workstations:
			for row in workstations:
				if row.workstation:
					self.append("custom_alternative_workstations", {"workstation": row.workstation})
