# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest


@pytest.mark.order(26)
def test_alternative_workstation_query():
	# test default settings
	response = frappe.call(
		"frappe.desk.search.search_link",
		**{
			"doctype": "Workstation",
			"txt": "",
			"reference_doctype": "Job Card",
		},
	)
	assert len(response) == 10
	# test with inventory tools settings
	inventory_tools_settings = frappe.get_doc(
		"Inventory Tools Settings", frappe.defaults.get_defaults().get("company")
	)
	inventory_tools_settings.allow_alternative_workstations = (
		"Allow Manually Defined Alternative Workstations"
	)
	inventory_tools_settings.save()
	response = frappe.call(
		"frappe.desk.search.search_link",
		**{
			"doctype": "Workstation",
			"txt": "",
			"query": "inventory_tools.inventory_tools.overrides.workstation.get_alternative_workstations",
			"filters": {"operation": "Gather Pie Filling Ingredients"},
			"reference_doctype": "Job Card",
		},
	)
	assert len(response) == 2
	assert response[0].get("value") == "Food Prep Table 1"  # default returns first
	assert "Default" in response[0].get("description")
	assert response[1].get("value") == "Food Prep Table 2"


@pytest.mark.order(27)
def test_alternative_workstation_by_type_query():
	# test default settings
	response = frappe.call(
		"frappe.desk.search.search_link",
		**{
			"doctype": "Workstation",
			"txt": "",
			"reference_doctype": "Job Card",
		},
	)
	assert len(response) == 10

	# test with inventory tools settings based on Workstation Type
	inventory_tools_settings = frappe.get_doc(
		"Inventory Tools Settings", frappe.defaults.get_defaults().get("company")
	)
	inventory_tools_settings.allow_alternative_workstations = (
		"Allow Alternative Workstations Based on Workstation Type"
	)
	inventory_tools_settings.save()

	response = frappe.call(
		"frappe.desk.search.search_link",
		**{
			"doctype": "Workstation",
			"txt": "",
			"query": "inventory_tools.inventory_tools.overrides.workstation.get_alternative_workstations",
			"filters": {"operation": "Gather Pie Filling Ingredients"},
			"reference_doctype": "Job Card",
		},
	)

	# Adjust these assertions based on your test data for workstation types
	assert len(response) >= 2
	workstation_values = [r.get("value") for r in response]
	assert "Food Prep Table 1" in workstation_values
	assert "Food Prep Table 2" in workstation_values
