# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

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
