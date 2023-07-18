import frappe
from erpnext.manufacturing.doctype.bom.bom import get_children as get_bom_children
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
from frappe import _, msgprint
from frappe.utils import flt, get_link_to_form, getdate, nowdate


class InventoryToolsWorkOrder(WorkOrder):
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
					_(
						f"This Work Order requires subcontracted items, and BOM operations were detected for the following ones:<br><ul><li>{formatted_items}</li></ul><br>Subcontracted item BOMs should not include operations."
					)
				)
			if self.skip_transfer:
				frappe.throw(
					_("Skip Material Transfer may not be selected when subcontracted items are present.")
				)

		return super().validate()

	def on_cancel(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		is_sc = frappe.get_value("Item", self.production_item, "is_sub_contracted_item")
		existing_po = in_existing_po(self.name)

		if settings and settings.enable_work_order_subcontracting and is_sc and len(existing_po) > 0:
			po = frappe.get_doc("Purchase Order", existing_po[0])

			if po.docstatus == 0:  # amend draft PO workflow
				po.flags.ignore_mandatory = True
				po.flags.ignore_validate = True
				# TODO: make adjustments to Items table or leave alone for user to handle?
				for item_row in po.get("items"):
					if (
						item_row.get("fg_item") == self.production_item and item_row.get("fg_item_qty") >= self.qty
					):
						item_row.fg_item_qty -= self.qty
						# TODO: check/adjust for UOMs? Will this work in scenarios where the 'item' uom is diff (hours vs. Nos)?
						item_row.qty -= self.qty
						item_row.stock_qty -= self.qty
						break
				for wo_row in po.get("subcontracting"):
					if wo_row.work_order == self.name:
						po.remove(wo_row)
						break
				po.calculate_taxes_and_totals()
				po.save()
				msgprint(
					_(
						f"Subcontracting Purchase Order {get_link_to_form('Purchase Order', po.name)} modified to remove Work Order {self.name}"
					),
					alert=True,
					indicator="green",
				)

		return super().on_cancel()

	def get_sub_contracted_items(self):
		"""
		Returns a list of (item_code, bom_no) for subcontracted items only. Checks the item
		in the work oder itself as well as sub assembly items
		"""
		bom_data = []
		get_sub_assembly_items(self.bom_no, bom_data, self.qty, self.company)
		sc_items = [(d.production_item, d.bom_no) for d in bom_data if d.is_sub_contracted_item]
		if frappe.get_value("Item", self.production_item, "is_sub_contracted_item"):
			sc_items.append((self.production_item, self.bom_no))
		return sc_items


@frappe.whitelist()
def make_subcontracted_purchase_order(wo_name):
	company, production_item = frappe.get_value("Work Order", wo_name, ["company", "production_item"])
	settings = frappe.get_doc("Inventory Tools Settings", {"company": company})
	is_sc = frappe.get_value("Item", production_item, "is_sub_contracted_item")

	if settings and settings.enable_work_order_subcontracting and is_sc:
		frappe.flags.mute_messages = False
		existing_po = in_existing_po(wo_name)
		if len(existing_po) > 0:
			msgprint(_(f"Work Order items are already included in Purchase Order {existing_po[0]}"))
		else:
			po = make_purchase_order(wo_name)
			msgprint(
				_(f"Subcontracting Purchase Order {get_link_to_form('Purchase Order', po)} created"),
				alert=True,
				indicator="green",
			)
	elif not settings:
		msgprint(_("Unable to create Purchase Order: no Inventory Tools Settings detected."))
	elif not settings.enable_work_order_subcontracting:
		msgprint(
			_(
				"Unable to create Purchase Order: Enable Work Order Subcontracting not set in Inventory Tools Settings."
			)
		)
	else:
		msgprint(
			_(
				f"Unable to create Purchase Order: the production item '{production_item}' is not set as a subcontracted item in the Item master."
			)
		)


def in_existing_po(wo_name):
	po = frappe.qb.DocType("Purchase Order")
	po_sub = frappe.qb.DocType("Purchase Order Subcontracting Detail")

	query = (
		frappe.qb.from_(po)
		.inner_join(po_sub)
		.on(po.name == po_sub.parent)
		.select(po.name)
		.where(po.docstatus != 2)
		.where(po.is_subcontracted == 1)
		.where(po_sub.work_order == wo_name)
	).get_sql()

	return frappe.db.sql(query, pluck="name")


def create_po_table_data(wo_name):
	wo = frappe.get_doc("Work Order", wo_name)
	item_row_data = {
		"fg_item": wo.production_item,
		"fg_item_qty": wo.qty,
		"warehouse": wo.fg_warehouse,
		"bom": wo.bom_no,
		"schedule_date": getdate(wo.planned_start_date) if wo.planned_start_date else nowdate(),
		"qty": wo.qty,
		"description": wo.description,
	}

	subc_row_data = {
		"work_order": wo_name,
		"item_name": wo.item_name,
		"fg_item": wo.production_item,
		"fg_item_qty": wo.qty,
		"bom": wo.bom_no,
		"stock_uom": wo.stock_uom,
	}

	return item_row_data, subc_row_data


def make_purchase_order(wo_name):
	wo = frappe.get_doc("Work Order", wo_name)

	# Get supplier
	supplier = frappe.get_value("Item Default", {"parent": wo.production_item}, "default_supplier")
	if not supplier:
		supplier = frappe.get_all(
			"Item Supplier", {"parent": wo.production_item}, "supplier", pluck="supplier"
		)
		try:
			supplier = supplier[-1]
		except IndexError as e:
			frappe.throw(
				_(f"Default Supplier or Item Supplier must be set for subcontracted item {wo.production_item}")
			)

	# Make Purchase Order
	po = frappe.new_doc("Purchase Order")
	po.company = wo.company
	po.supplier = supplier
	po.schedule_date = getdate(wo.planned_start_date) if wo.planned_start_date else nowdate()
	po.is_subcontracted = 1
	item_row_data, subc_row_data = create_po_table_data(wo_name)
	po.append("items", item_row_data)
	po.append("subcontracting", subc_row_data)
	po.set_missing_values()
	po.flags.ignore_mandatory = True
	po.flags.ignore_validate = True
	po.insert()
	return po.name


@frappe.whitelist()
def add_to_existing_purchase_order(wo_name, po_name):
	po = frappe.get_doc("Purchase Order", po_name)
	company, production_item, wo_qty = frappe.get_value(
		"Work Order", wo_name, ["company", "production_item", "qty"]
	)
	settings = frappe.get_doc("Inventory Tools Settings", {"company": company})
	if settings and settings.enable_work_order_subcontracting and po.get("is_subcontracted"):
		frappe.flags.mute_messages = False
		existing_po = in_existing_po(wo_name)
		if len(existing_po) > 0:
			msgprint(_(f"Work Order items are already included in Purchase Order {existing_po[0]}"))
			return
		else:
			item_row_data, subc_row_data = create_po_table_data(wo_name)
			if po.docstatus == 2:
				frappe.throw(_("Unable to add to the selected Purchase Order because it is cancelled."))
			elif po.docstatus == 0:  # amend draft PO workflow
				po.append("items", item_row_data)
				po.append("subcontracting", subc_row_data)
				po.set_missing_values()
				po.flags.ignore_mandatory = True
				po.flags.ignore_validate = True
				po.save()
				msgprint(
					_(
						f"Added items to subcontracting Purchase Order {get_link_to_form('Purchase Order', po.name)}."
					),
					alert=True,
					indicator="green",
				)
				return
			else:  # cancel / amend submitted PO workflow. Leaves amended PO in Draft status so user can make adjustments as needed to Items table
				po.cancel()
				new_po = frappe.copy_doc(po)
				new_po.amended_from = po.name
				new_po.status = "Draft"
				new_po.append("items", item_row_data)
				new_po.append("subcontracting", subc_row_data)
				new_po.flags.ignore_mandatory = True
				new_po.flags.ignore_validate = True
				new_po.insert()
				msgprint(
					_(
						f"Added items to revised subcontracting Purchase Order {get_link_to_form('Purchase Order', new_po.name)}."
					),
					alert=True,
					indicator="green",
				)
				return
	elif not settings:
		msgprint(_("Unable to create Purchase Order: no Inventory Tools Settings detected."))
		return
	elif not settings.enable_work_order_subcontracting:
		msgprint(
			_(
				"Unable to create Purchase Order: Enable Work Order Subcontracting not set in Inventory Tools Settings."
			)
		)
		return
	else:
		msgprint(
			_(
				f"Unable to create Purchase Order: the production item '{production_item}' is not set as a subcontracted item in the Item master."
			)
		)
		return


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
						"production_item": d.item_code,
						"bom_no": d.value,
						"is_sub_contracted_item": d.is_sub_contracted_item,
						"bom_level": indent,
						"indent": indent,
					}
				)
			)

			if d.value:
				get_sub_assembly_items(d.value, bom_data, stock_qty, company, indent=indent + 1)
