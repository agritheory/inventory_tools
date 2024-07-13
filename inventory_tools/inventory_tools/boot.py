import frappe


def boot_session(bootinfo):
	bootinfo.inventory_tools_settings = {}
	for company in frappe.get_all("Inventory Tools Settings", pluck="company"):
		settings = frappe.get_doc("Inventory Tools Settings", company)
		bootinfo.inventory_tools_settings[company] = settings
