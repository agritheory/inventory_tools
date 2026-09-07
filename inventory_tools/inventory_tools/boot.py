# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe


def boot_session(bootinfo):
	bootinfo.inventory_tools_settings = {}
	for company in frappe.get_all("Inventory Tools Settings", pluck="company"):
		bootinfo.inventory_tools_settings[company] = frappe.get_doc(
			"Inventory Tools Settings", company
		).as_dict()
