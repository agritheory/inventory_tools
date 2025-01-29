import frappe
from frappe.model.rename_doc import rename_doc


def execute():
	if frappe.db.exists("DocType", "Alternative Workstations"):
		rename_doc(
			"DocType", "Alternative Workstations", "Alternative Workstation", ignore_if_exists=True
		)

	frappe.reload_doc("inventory_tools", "doctype", "alternative_workstation", force=True)
