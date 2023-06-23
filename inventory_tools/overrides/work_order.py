import frappe
from erpnext.manufacturing.doctype.bom.bom import get_children as get_bom_children
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
from frappe import _, msgprint
from frappe.utils import flt, get_link_to_form, getdate, nowdate


class CustomWorkOrder(WorkOrder):
	def validate(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		if (
			settings.enable_work_order_subcontracting
			and self.has_sub_contracted_items()
			and self.skip_transfer
		):
			frappe.throw(_("Skip Material Transfer may not be selected when sub-contracted items present."))

		super().validate()

	def on_submit(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		if settings.enable_work_order_subcontracting:
			po_list = []
			subcontracted_po = self.get_sub_contracted_sub_assembly_items()
			self.make_subcontracted_purchase_order(subcontracted_po, po_list)
			if po_list:
				frappe.flags.mute_messages = False
				for doc in po_list:
					msgprint(
						_(f"Subcontracting Purchase Order {get_link_to_form('Purchase Order', doc.name)} created"),
						alert=True,
					)

		super().on_submit()

	def has_sub_contracted_items(self):
		bom_data = []
		get_sub_assembly_items(self.bom_no, bom_data, self.qty, self.company)
		return len([d.production_item for d in bom_data if d.is_sub_contracted_item]) > 0

	def make_subcontracted_purchase_order(self, subcontracted_po, purchase_orders):
		if not subcontracted_po:
			return

		for supplier, po_list in subcontracted_po.items():
			po = frappe.new_doc("Purchase Order")
			po.company = self.company
			po.supplier = supplier
			po.schedule_date = getdate(self.planned_start_date) if self.planned_start_date else nowdate()
			po.is_subcontracted = 1
			for item in po_list:
				po_data = {
					"fg_item": item.production_item,
					"warehouse": item.fg_warehouse,
					"bom": item.bom_no,
					"fg_item_qty": item.qty,
					"work_order": self.name,
					"work_order_sub_assembly_item": item.production_item,
				}

				for field in [
					"schedule_date",
					"qty",
					"description",
				]:
					po_data[field] = item.get(field)

				po.append("items", po_data)

				wo_data = {
					"work_order": self.name,
					"work_order_sub_assembly_item": item.production_item,
					"qty": item.qty,
					"bom": item.bom_no,
					"stock_uom": item.stock_uom,
					"uom": item.uom,
					"conversion_factor": 1,
					"stock_qty": item.stock_qty,
					"fg_item": item.production_item,
					"fg_item_qty": item.qty,
					"warehouse": item.fg_warehouse,
				}

				po.append("subcontracting", wo_data)

			po.set_missing_values()
			po.flags.ignore_mandatory = True
			po.flags.ignore_validate = True
			po.insert()
			purchase_orders.append(po.name)

	def get_sub_contracted_sub_assembly_items(self):
		"""
		Fetch sub assembly items, filter for subcontracted ones, restructure into dict by supplier
		"""
		sub_assembly_items_store = []
		bom_data = []
		subcontracted_po = {}

		# Recursively collect sub-assembly BOM data
		get_sub_assembly_items(self.bom_no, bom_data, self.qty, self.company)

		for data in bom_data:
			data.qty = data.stock_qty
			# data.production_plan_item = row.name  # prod plan table name, ie: 7ec863e...
			data.fg_warehouse = self.fg_warehouse
			data.schedule_date = self.planned_start_date
			data.type_of_manufacturing = "Subcontract" if data.is_sub_contracted_item else "In House"

		sub_assembly_items_store = [d for d in bom_data if d.is_sub_contracted_item]
		sub_assembly_items_store.sort(key=lambda d: d.bom_level, reverse=True)  # sort by bom level

		# Set supplier
		for d in sub_assembly_items_store:
			supplier = frappe.get_value("Item Default", {"parent": d.production_item}, "default_supplier")
			if not supplier:
				supplier = frappe.get_all(
					"Item Supplier", {"parent": d.production_item}, "supplier", pluck="supplier"
				)
				try:
					supplier = supplier[-1]
				except IndexError as e:
					frappe.throw(
						_(
							f"Default Supplier or Item Supplier must be set for subcontracted item {d.production_item}"
						)
					)
			d.supplier = supplier

		# Build dict with supplier keys
		for d in sub_assembly_items_store:
			subcontracted_po.setdefault(d.supplier, []).append(d)
		return subcontracted_po


def get_sub_assembly_items(bom_no, bom_data, to_produce_qty, company, warehouse=None, indent=0):
	data = get_bom_children(parent=bom_no)
	for d in data:
		if d.expandable:
			parent_item_code = frappe.get_cached_value("BOM", bom_no, "item")
			stock_qty = (d.stock_qty / d.parent_bom_qty) * flt(to_produce_qty)

			bom_data.append(
				frappe._dict(
					{
						"parent_item_code": parent_item_code,
						"description": d.description,
						"production_item": d.item_code,
						"item_name": d.item_name,
						"stock_uom": d.stock_uom,
						"uom": d.stock_uom,
						"bom_no": d.value,
						"is_sub_contracted_item": d.is_sub_contracted_item,
						"bom_level": indent,
						"indent": indent,
						"stock_qty": stock_qty,
					}
				)
			)

			if d.value:
				get_sub_assembly_items(d.value, bom_data, stock_qty, company, warehouse, indent=indent + 1)
