import frappe


def validate_alternative_workstation(self, method):
	if self.workstation:
		for row in self.alternative_workstations:
			if row.workstation == self.workstation:
				frappe.throw("Default Workstation should not be selected as alternative workstation")
