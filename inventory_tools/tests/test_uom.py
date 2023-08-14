import frappe
import pytest


@pytest.mark.xfail()
def test_uom_enforcement_validation():
	so = frappe.get_last_doc("Sales Order")
	assert so.items[0].uom == "Nos"
	so.items[0].uom = "Box"
	so.save()
