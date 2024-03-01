import json

import frappe

"""
	This function fetch workstation of the document operation.
	In Operation you can select multiple workstations in Alternative Workstation field. 
	In the Work Order, Operation table, and Jobcard, there exists an operation field. 
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
@frappe.validate_and_sanitize_search_inputs
def get_alternative_workstations(doctype, txt, searchfield, start, page_len, filters):
	operation = filters.get("operation")
	if not operation:
		frappe.throw("Please select a Operation first.")

	if txt:
		searchfields = frappe.get_meta(doctype).get_search_fields()
		searchfields = " or ".join(["ws." + field + f" LIKE '%{txt}%'" for field in searchfields])

	conditions = ""
	if txt and searchfields:
		conditions = f"and ({searchfields})"

	workstation = frappe.db.sql(
		"""
		Select aw.workstation, ws.workstation_type, ws.description
		From `tabOperation` as op
		Left Join `tabAlternative Workstations` as aw ON aw.parent = op.name
		Left Join `tabWorkstation` as ws ON ws.name = aw.workstation
		Where op.name = '{operation}' {conditions}
	""".format(
			conditions=conditions, operation=operation
		)
	)

	default_workstation = frappe.db.get_value("Operation", operation, "workstation")
	flag = True
	for row in workstation:
		if row[0] == None:
			workstation = ((default_workstation,),)
			flag = False
	if flag:
		workstation += ((default_workstation,),)
	return workstation
