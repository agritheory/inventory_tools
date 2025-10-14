# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe


def refresh_workstation_rates():
	workstations = frappe.get_all("Workstation", fields=["name"])
	for ws in workstations:
		doc = frappe.get_doc("Workstation", ws.name)
		# Trigger validate to recalc latest rates
		doc.validate()
		doc.save()
