import frappe
import pytest


@pytest.mark.order(45)
def test_alternative_workstation_query():
	# test default settings
	frappe.call(
		"frappe.desk.search.search_link",
		**{
			"doctype": "Workstation",
			"txt": "",
			"reference_doctype": "Job Card",
		},
	)
	assert len(frappe.response.results) == 16  # all workstations

	# test with inventory tools settings
	inventory_tools_settings = frappe.get_doc(
		"Inventory Tools Settings", frappe.defaults.get_defaults().get("company")
	)
	inventory_tools_settings.allow_alternative_workstations = True
	inventory_tools_settings.save()
	frappe.call(
		"frappe.desk.search.search_link",
		**{
			"doctype": "Workstation",
			"txt": "",
			"query": "inventory_tools.inventory_tools.overrides.workstation.get_alternative_workstations",
			"filters": {"operation": "Gather Pie Filling Ingredients"},
			"reference_doctype": "Job Card",
		},
	)
	assert len(frappe.response.results) == 2
	assert frappe.response.results[0].get("value") == "Food Prep Table 1"  # default returns first
	assert "Default" in frappe.response.results[0].get("description")
	assert frappe.response.results[1].get("value") == "Food Prep Table 2"
