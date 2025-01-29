import frappe
import pytest
from frappe.exceptions import ValidationError


@pytest.mark.order(40)
def test_uom_enforcement_validation():
	_so = frappe.get_last_doc("Sales Order")
	inventory_tools_settings = frappe.get_doc("Inventory Tools Settings", _so.company)
	inventory_tools_settings.enforce_uoms = True
	inventory_tools_settings.save()

	so = frappe.copy_doc(_so)
	assert so.items[0].uom == "Nos"
	so.items[0].uom = "Box"
	with pytest.raises(ValidationError) as exc_info:
		so.save()

	assert "Invalid UOM" in exc_info.value.args[0]


@pytest.mark.order(41)
def test_uom_enforcement_query():
	inventory_tools_settings = frappe.get_doc(
		"Inventory Tools Settings", frappe.defaults.get_defaults().get("company")
	)
	inventory_tools_settings.enforce_uoms = True
	inventory_tools_settings.save()
	frappe.call(
		"frappe.desk.search.search_link",
		**{
			"doctype": "UOM",
			"txt": "",
			"query": "inventory_tools.inventory_tools.overrides.uom.uom_restricted_query",
			"filters": {"parent": "Parchment Paper"},
			"reference_doctype": "Purchase Order Item",
		},
	)
	assert len(frappe.response.results) == 2
	assert frappe.response.results[0].get("value") == "Nos"
	assert frappe.response.results[0].get("description") == "1.0"
	assert frappe.response.results[1].get("value") == "Box"
	assert frappe.response.results[1].get("description") == "100.0"
