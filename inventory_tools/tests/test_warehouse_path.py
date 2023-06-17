import pytest
import frappe


"""
This should be generated as part of the setup script
"""
@pytest.mark.order(1)
def test_warehouse_path():
	wh = frappe.get_doc('Warehouse', '')
	assert wh.warehouse_path = ''
