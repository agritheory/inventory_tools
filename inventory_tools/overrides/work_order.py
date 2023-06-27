import frappe
from erpnext.manufacturing.doctype.bom.bom import get_children as get_bom_children
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
from frappe.utils import flt


class CustomWorkOrder(WorkOrder):
	def validate(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		sc_items = self.get_sub_contracted_items()
		if settings and settings.enable_work_order_subcontracting and sc_items:
			has_ops = [
				item for item, bom_no in sc_items if frappe.get_value("BOM", bom_no, "with_operations")
			]
			if has_ops:
				formatted_items = "</li><li>".join(has_ops)
				frappe.throw(
					frappe._(
						f"This Work Order requires subcontracted items, and BOM operations were detected for the following ones:<br><ul><li>{formatted_items}</li></ul><br>Subcontracted item BOMs should not include operations."
					)
				)
			if self.skip_transfer:
				frappe.throw(
					frappe._("Skip Material Transfer may not be selected when subcontracted items are present.")
				)

		super().validate()

	def get_sub_contracted_items(self):
		"""
		Returns a list of (item_code, bom_no) for subcontracted items, including the item
		in the work oder itself (if subcontracted) as well as any subcontracted sub assembly
		items
		"""
		bom_data = []
		get_sub_assembly_items(self.bom_no, bom_data, self.qty, self.company)
		sc_items = [(d.production_item, d.bom_no) for d in bom_data if d.is_sub_contracted_item]
		if frappe.get_value("Item", self.production_item, "is_sub_contracted_item"):
			sc_items.append((self.production_item, self.bom_no))
		return sc_items


def get_sub_assembly_items(bom_no, bom_data, to_produce_qty, company, indent=0):
	"""
	Recursively collects sub-assembly item BOM data for a given 'parent' BOM (`bom_no`)
	"""
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
				get_sub_assembly_items(d.value, bom_data, stock_qty, company, indent=indent + 1)
