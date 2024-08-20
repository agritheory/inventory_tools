# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from erpnext.manufacturing.doctype.production_plan.production_plan import ProductionPlan
from erpnext.manufacturing.doctype.work_order.work_order import get_default_warehouse


class InventoryToolsProductionPlan(ProductionPlan):
	@frappe.whitelist()
	def make_work_order(self):
		"""
		HASH: 30c0b2bb546c1c78bd5db29311a78d71a02efdf1
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/production_plan/production_plan.py
		METHOD: make_work_order
		"""

		wo_list, po_list = [], []
		subcontracted_po = {}
		default_warehouses = get_default_warehouse()

		self.make_work_order_for_finished_goods(wo_list, default_warehouses)
		self.make_work_order_for_subassembly_items(wo_list, subcontracted_po, default_warehouses)
		if frappe.get_value("Inventory Tools Settings", self.company, "create_purchase_orders"):
			self.make_subcontracted_purchase_order(subcontracted_po, po_list)
		self.show_list_created_message("Work Order", wo_list)
		self.show_list_created_message("Purchase Order", po_list)

		if not wo_list:
			frappe.msgprint(_("No Work Orders were created"))

	def make_work_order_for_subassembly_items(self, wo_list, subcontracted_po, default_warehouses):
		"""
		HASH: 30c0b2bb546c1c78bd5db29311a78d71a02efdf1
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/production_plan/production_plan.py
		METHOD: make_work_order_for_subassembly_items
		"""

		for row in self.sub_assembly_items:
			if row.type_of_manufacturing == "Subcontract":
				subcontracted_po.setdefault(row.supplier, []).append(row)
				if not frappe.get_value(
					"Inventory Tools Settings", self.company, "enable_work_order_subcontracting"
				):
					continue

			if row.type_of_manufacturing == "Material Request":
				continue

			work_order_data = {
				"wip_warehouse": default_warehouses.get("wip_warehouse"),
				"fg_warehouse": default_warehouses.get("fg_warehouse"),
				"company": self.get("company"),
			}

			self.prepare_data_for_sub_assembly_items(row, work_order_data)
			work_order = self.create_work_order(work_order_data)
			if work_order:
				wo_list.append(work_order)
