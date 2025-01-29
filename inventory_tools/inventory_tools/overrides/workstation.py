import frappe
from frappe.desk.reportview import execute
from frappe.desk.search import search_link

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
@frappe.read_only()
@frappe.validate_and_sanitize_search_inputs
def get_alternative_workstations(doctype, txt, searchfield, start, page_len, filters):
	company = filters.get("company") or frappe.defaults.get_defaults().get("company")
	if not frappe.get_cached_value(
		"Inventory Tools Settings", company, "allow_alternative_workstations"
	):
		filters.pop("operation") if "operation" in filters else True
		filters.pop("company") if "company" in filters else True
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
		frappe.throw("Please select a Operation first.")

	searchfields = list(reversed(frappe.get_meta(doctype).get_search_fields()))
	select = ",\n".join([f"`tabWorkstation`.{field}" for field in searchfields])
	search_text = "AND `tabAlternative Workstation`.workstation LIKE %(txt)s" if txt else ""

	workstation = frappe.db.sql(
		f"""
		SELECT DISTINCT {select}
		FROM `tabOperation`, `tabWorkstation`, `tabAlternative Workstation`
		WHERE `tabWorkstation`.name = `tabAlternative Workstation`.workstation
		AND `tabAlternative Workstation`.parent = %(operation)s
		{search_text}
	""",
		{"operation": operation, "txt": f"%{txt}%"},
		as_list=True,
	)

	default_workstation_name = frappe.db.get_value("Operation", operation, "workstation")
	default_workstation_fields = frappe.db.get_values(
		"Workstation", default_workstation_name, searchfields, as_dict=True
	)
	if default_workstation_name not in [row[0] for row in workstation]:
		_default = tuple(
			[
				default_workstation_fields[0].name,
				f"{frappe.bold('Default')} - {','.join([v for k, v in default_workstation_fields[0].items() if k != 'name'])}",
			]
		)
		workstation.insert(0, _default)
	return workstation
