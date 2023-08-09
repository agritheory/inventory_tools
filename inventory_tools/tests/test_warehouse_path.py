import frappe
import pytest

"""
This should be generated as part of the setup script
"""


@pytest.mark.order(1)
def test_warehouse_path():
	wh = frappe.get_doc("Warehouse", "Bakery Display - APC")
	assert wh.warehouse_path == "Finished Goods ⇒ Bakery Display"
	wh.parent_warehouse = "All Warehouses - APC"
	wh.save()
	assert wh.warehouse_path == "Bakery Display"
	wh.parent_warehouse = "Baked Goods - APC"
	wh.save()
	assert wh.warehouse_path == "Finished Goods ⇒ Bakery Display"
