import frappe
import pytest


@pytest.mark.order(1)
def test_warehouse_path():
	"""
	In the setup script this feature is turned on
	"""
	wh = frappe.get_doc("Warehouse", "Bakery Display - APC")
	assert wh.warehouse_path == "Finished Goods ⇒ Bakery Display"
	wh.parent_warehouse = "All Warehouses - APC"
	wh.save()
	assert wh.warehouse_path == "Bakery Display"
	wh.parent_warehouse = "Baked Goods - APC"
	wh.save()
	assert wh.warehouse_path == "Finished Goods ⇒ Bakery Display"
