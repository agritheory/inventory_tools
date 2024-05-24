import frappe
from erpnext.manufacturing.doctype.work_order.work_order import (
	OverProductionError,
	StockOverProductionError,
	WorkOrder,
)
from erpnext.manufacturing.doctype.work_order.work_order import (
	make_stock_entry as _make_stock_entry,
)
from frappe import _
from frappe.utils import flt, get_link_to_form, getdate


class InventoryToolsWorkOrder(WorkOrder):
	def onload(self):
		"""
		HASH: 4d34b1ead73baf4c5430a2ecbe44b9e8468d7626
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/work_order/work_order.py
		METHOD: onload
		"""

		ms = frappe.get_doc("Manufacturing Settings")
		self.set_onload("material_consumption", ms.material_consumption)
		self.set_onload("backflush_raw_materials_based_on", ms.backflush_raw_materials_based_on)
		self.set_onload("overproduction_percentage", get_allowance_percentage(self.company, self.bom_no))

	def validate(self):
		if self.is_work_order_subcontracting_enabled() and frappe.get_value(
			"BOM", self.bom_no, "is_subcontracted"
		):
			self.validate_subcontracting_no_bom_ops()
			self.validate_subcontracting_no_skip_transfer()
		return super().validate()

	def on_cancel(self):
		if self.is_work_order_subcontracting_enabled():
			self.on_cancel_remove_wo_from_po()
		return super().on_cancel()

	def is_work_order_subcontracting_enabled(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		return bool(settings and settings.enable_work_order_subcontracting)

	def validate_subcontracting_no_bom_ops(self):
		if frappe.get_value("BOM", self.bom_no, "with_operations"):
			frappe.throw(
				frappe._(
					"This Work Order uses a BOM that's subcontracted, and BOM operations were detected. Subcontracted item BOMs should not include operations."
				)
			)

	def validate_subcontracting_no_skip_transfer(self):
		if self.skip_transfer:
			frappe.throw(
				frappe._(
					"Skip Material Transfer may not be selected when the Work Order uses a BOM that is subcontracted."
				)
			)

	def on_cancel_remove_wo_from_po(self):
		is_sc = frappe.get_value("BOM", self.bom_no, "is_subcontracted")
		existing_po = in_existing_po(self.name)

		if is_sc and len(existing_po) > 0:
			po = frappe.get_doc("Purchase Order", existing_po[0])

			if po.docstatus == 0:  # amend draft PO workflow
				po.flags.ignore_mandatory = True
				po.flags.ignore_validate = True
				for item_row in po.get("items"):
					if (
						item_row.get("fg_item") == self.production_item and item_row.get("fg_item_qty") >= self.qty
					):
						item_row.fg_item_qty -= self.qty

						qty_cf, q_msg = get_uom_cf(item_row.get("fg_item"), self.stock_uom, item_row.uom)
						stock_qty_cf, sq_msg = get_uom_cf(
							item_row.get("fg_item"), self.stock_uom, item_row.stock_uom
						)
						item_row.qty -= self.qty * qty_cf
						item_row.stock_qty -= self.qty * stock_qty_cf
						break
				for wo_row in po.get("subcontracting"):
					if wo_row.work_order == self.name:
						po.remove(wo_row)
						break
				po.calculate_taxes_and_totals()
				po.save()
				frappe.msgprint(
					frappe._(
						f"Subcontracting Purchase Order {get_link_to_form('Purchase Order', po.name)} modified to remove Work Order {self.name}. {q_msg or sq_msg}"
					),
					alert=True,
					indicator="green",
				)

	def create_job_card(self):
		create_job_cards_automatically = (
			frappe.db.get_value("BOM", self.bom_no, "create_job_cards_automatically")
			or frappe.db.get_value(
				"Inventory Tools Settings", {"company": self.company}, "create_job_cards_automatically"
			)
			or "Yes"
		)

		if create_job_cards_automatically == "No":
			return
		return super().create_job_card()

	def update_work_order_qty(self):
		"""
		HASH: 4d34b1ead73baf4c5430a2ecbe44b9e8468d7626
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/work_order/work_order.py
		METHOD: update_work_order_qty

		Update **Manufactured Qty** and **Material Transferred for Qty** in Work Order
		based on Stock Entry
		"""

		allowance_percentage = get_allowance_percentage(self.company, self.bom_no)

		for purpose, fieldname in (
			("Manufacture", "produced_qty"),
			("Material Transfer for Manufacture", "material_transferred_for_manufacturing"),
		):
			if (
				purpose == "Material Transfer for Manufacture"
				and self.operations
				and self.transfer_material_against == "Job Card"
			):
				continue

			qty = self.get_transferred_or_manufactured_qty(purpose)

			completed_qty = self.qty + (allowance_percentage / 100 * self.qty)
			if qty > completed_qty:
				frappe.throw(
					_("{0} ({1}) cannot be greater than planned quantity ({2}) in Work Order {3}").format(
						self.meta.get_label(fieldname), qty, completed_qty, self.name
					),
					StockOverProductionError,
				)

			self.db_set(fieldname, qty)
			self.set_process_loss_qty()

			from erpnext.selling.doctype.sales_order.sales_order import update_produced_qty_in_so_item

			if self.sales_order and self.sales_order_item:
				update_produced_qty_in_so_item(self.sales_order, self.sales_order_item)

		if self.production_plan:
			self.update_production_plan_status()

	def update_operation_status(self):
		"""
		HASH: 4d34b1ead73baf4c5430a2ecbe44b9e8468d7626
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/work_order/work_order.py
		METHOD: update_operation_status
		"""

		allowance_percentage = get_allowance_percentage(self.company, self.bom_no)
		max_allowed_qty_for_wo = flt(self.qty) + (allowance_percentage / 100 * flt(self.qty))

		for d in self.get("operations"):
			if not d.completed_qty:
				d.status = "Pending"
			elif flt(d.completed_qty) < flt(self.qty):
				d.status = "Work in Progress"
			elif flt(d.completed_qty) == flt(self.qty):
				d.status = "Completed"
			elif flt(d.completed_qty) <= max_allowed_qty_for_wo:
				d.status = "Completed"
			else:
				frappe.throw(_("Completed Qty cannot be greater than 'Qty to Manufacture'"))

	def validate_qty(self):
		"""
		HASH: 4d34b1ead73baf4c5430a2ecbe44b9e8468d7626
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/work_order/work_order.py
		METHOD: validate_qty
		"""

		if not self.qty > 0:
			frappe.throw(_("Quantity to Manufacture must be greater than 0."))

		if (
			self.production_plan
			and self.production_plan_item
			and not self.production_plan_sub_assembly_item
		):
			qty_dict = frappe.db.get_value(
				"Production Plan Item", self.production_plan_item, ["planned_qty", "ordered_qty"], as_dict=1
			)

			if not qty_dict:
				return

			allowance_qty = (
				get_allowance_percentage(self.company, self.bom_no) / 100 * qty_dict.get("planned_qty", 0)
			)

			max_qty = qty_dict.get("planned_qty", 0) + allowance_qty - qty_dict.get("ordered_qty", 0)

			if not max_qty > 0:
				frappe.throw(
					_("Cannot produce more item for {0}").format(self.production_item), OverProductionError
				)
			elif self.qty > max_qty:
				frappe.throw(
					_("Cannot produce more than {0} items for {1}").format(max_qty, self.production_item),
					OverProductionError,
				)


@frappe.whitelist()
def make_subcontracted_purchase_order(wo_name, supplier=None):
	company, bom_no = frappe.get_value("Work Order", wo_name, ["company", "bom_no"])
	settings = frappe.get_doc("Inventory Tools Settings", {"company": company})
	is_sc = frappe.get_value("BOM", bom_no, "is_subcontracted")

	if settings and settings.enable_work_order_subcontracting and is_sc:
		frappe.flags.mute_messages = False
		existing_po = in_existing_po(wo_name)
		if len(existing_po) > 0:
			frappe.msgprint(
				frappe._(f"Work Order items are already included in Purchase Order {existing_po[0]}")
			)
		else:
			po = make_purchase_order(wo_name, supplier)
			frappe.msgprint(
				frappe._(f"Subcontracting Purchase Order {get_link_to_form('Purchase Order', po)} created"),
				alert=True,
				indicator="green",
			)
			return po
	elif not settings:
		frappe.msgprint(
			frappe._("Unable to create Purchase Order: no Inventory Tools Settings detected.")
		)
	elif not settings.enable_work_order_subcontracting:
		frappe.msgprint(
			frappe._(
				"Unable to create Purchase Order: Enable Work Order Subcontracting not set in Inventory Tools Settings."
			)
		)
	else:
		frappe.msgprint(
			frappe._("Unable to create Purchase Order: the Work Order's BOM is not set as subcontracted.")
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
		"item_code": wo.production_item,
		"fg_item": wo.production_item,
		"fg_item_qty": wo.qty,
		"warehouse": wo.fg_warehouse,
		"bom": wo.bom_no,
		"schedule_date": max(getdate(wo.planned_start_date), getdate()),
		"qty": wo.qty,
		"description": wo.description,
	}

	subc_row_data = {
		"work_order": wo_name,
		"warehouse": wo.fg_warehouse,
		"item_name": wo.item_name,
		"fg_item": wo.production_item,
		"fg_item_qty": wo.qty,
		"bom": wo.bom_no,
		"stock_uom": wo.stock_uom,
	}

	return item_row_data, subc_row_data


def make_purchase_order(wo_name, supplier=None):
	company, production_item, planned_start_date = frappe.get_value(
		"Work Order", wo_name, ["company", "production_item", "planned_start_date"]
	)

	# Get supplier
	if not supplier:
		supplier = frappe.get_value("Item Default", {"parent": production_item}, "default_supplier")
		if not supplier:
			supplier = frappe.get_all(
				"Item Supplier", {"parent": production_item}, "supplier", pluck="supplier"
			)
			try:
				supplier = supplier[-1]
			except IndexError as e:
				frappe.throw(
					frappe._(
						f"Default Supplier or Item Supplier must be set for subcontracted item {production_item}"
					)
				)
	wip_warehouse = frappe.db.get_value(
		"Subcontracting Default",
		{"parent": supplier, "company": company},
		["wip_warehouse"],
	)
	# Make Purchase Order
	po = frappe.new_doc("Purchase Order")
	po.company = company
	po.supplier = supplier
	po.schedule_date = max(getdate(planned_start_date), getdate())
	po.posting_date = getdate()
	po.supplier_warehouse = wip_warehouse
	po.is_subcontracted = 1
	item_row_data, subc_row_data = create_po_table_data(wo_name)
	po.append("items", item_row_data)
	po.append("subcontracting", subc_row_data)
	po.set_missing_values()
	po.save()
	return po.name


def get_uom_cf(fg_item_code, from_uom, to_uom):
	"""
	Finds the UOM Conversion Detail conversion factor for given item code, if it exists, otherwise returns 0.
	Returns the conversion factor and a status message (blank if CF found, explanation if not).
	"""
	message = ""
	if from_uom == to_uom:
		cf = 1
	else:
		cf = (
			frappe.get_value(
				"UOM Conversion Detail", {"parent": fg_item_code, "uom": to_uom}, "conversion_factor"
			)
			or 0
		)
	try:
		cf = 1 / cf
		return cf, message
	except ZeroDivisionError:
		message = f" PO Item quantities require manual adjustment - no UOM Conversion Detail exists to convert {fg_item_code} in {from_uom} to {to_uom}."
		return cf, message


@frappe.whitelist()
def add_to_existing_purchase_order(wo_name, po_name):
	po = frappe.get_doc("Purchase Order", po_name)
	company, production_item, wo_qty, wo_stock_uom = frappe.get_value(
		"Work Order", wo_name, ["company", "production_item", "qty", "stock_uom"]
	)
	settings = frappe.get_doc("Inventory Tools Settings", {"company": company})
	if settings and settings.enable_work_order_subcontracting and po.get("is_subcontracted"):
		frappe.flags.mute_messages = False
		existing_po = in_existing_po(wo_name)
		if len(existing_po) > 0:
			frappe.msgprint(
				frappe._(f"Work Order items are already included in Purchase Order {existing_po[0]}")
			)
			return
		else:
			item_row_data, subc_row_data = create_po_table_data(wo_name)
			if po.docstatus == 2:
				frappe.throw(frappe._("Unable to add to the selected Purchase Order because it is cancelled."))
			elif po.docstatus == 0:  # amend draft PO workflow
				for item in po.get("items"):
					if item.get("fg_item") == production_item:
						item.fg_item_qty += wo_qty
						qty_cf, q_msg = get_uom_cf(item.get("fg_item"), wo_stock_uom, item.uom)
						stock_qty_cf, sq_msg = get_uom_cf(item.get("fg_item"), wo_stock_uom, item.stock_uom)
						item.qty += wo_qty * qty_cf
						item.stock_qty += wo_qty * stock_qty_cf
						break
				else:
					po.append("items", item_row_data)
				po.append("subcontracting", subc_row_data)
				po.set_missing_values()
				po.flags.ignore_mandatory = True
				po.flags.ignore_validate = True
				po.save()
				frappe.msgprint(
					frappe._(
						f"Added items to subcontracting Purchase Order {get_link_to_form('Purchase Order', po.name)}. {q_msg or sq_msg}"
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
				for item in new_po.get("items"):
					if item.get("fg_item") == production_item:
						item.fg_item_qty += wo_qty
						qty_cf, q_msg = get_uom_cf(item.get("fg_item"), wo_stock_uom, item.uom)
						stock_qty_cf, sq_msg = get_uom_cf(item.get("fg_item"), wo_stock_uom, item.stock_uom)
						item.qty += wo_qty * qty_cf
						item.stock_qty += wo_qty * stock_qty_cf
						break
				else:
					new_po.append("items", item_row_data)
				new_po.append("subcontracting", subc_row_data)
				new_po.flags.ignore_mandatory = True
				new_po.flags.ignore_validate = True
				new_po.insert()
				frappe.msgprint(
					frappe._(
						f"Added items to revised subcontracting Purchase Order {get_link_to_form('Purchase Order', new_po.name)}. {q_msg or sq_msg}"
					),
					alert=True,
					indicator="green",
				)
				return
	elif not settings:
		frappe.msgprint(
			frappe._("Unable to create Purchase Order: no Inventory Tools Settings detected.")
		)
		return
	elif not settings.enable_work_order_subcontracting:
		frappe.msgprint(
			frappe._(
				"Unable to create Purchase Order: Enable Work Order Subcontracting not set in Inventory Tools Settings."
			)
		)
		return
	else:
		frappe.msgprint(
			frappe._(
				f"Unable to create Purchase Order: the production item '{production_item}' is not set as a subcontracted item in the Item master."
			)
		)
		return


@frappe.whitelist()
def make_stock_entry(work_order_id, purpose, qty=None):
	se = _make_stock_entry(work_order_id, purpose, qty)
	settings = frappe.get_doc("Inventory Tools Settings", {"company": se.get("company")})
	if not (settings and settings.enable_work_order_subcontracting):
		return se
	supplier = frappe.db.get_value("Work Order", work_order_id, "supplier")
	if supplier:
		wip_warehouse, return_warehouse = frappe.db.get_value(
			"Subcontracting Default",
			{"parent": supplier, "company": se.get("company")},
			["wip_warehouse", "return_warehouse"],
		)
		if purpose == "Material Transfer for Manufacture":
			for row in se.get("items"):
				row["t_warehouse"] = wip_warehouse
		elif purpose == "Manufacture":
			for row in se.get("items"):
				if not row.is_finished_item:
					row["s_warehouse"] = wip_warehouse
					row["t_warehouse"] = None
				else:
					row["s_warehouse"] = None
					row["t_warehouse"] = return_warehouse
	return se


def get_allowance_percentage(company: str, bom_no: str):
	bom_allowance_percentage = frappe.get_value(
		"BOM", bom_no, "overproduction_percentage_for_work_order"
	)
	if bom_allowance_percentage:
		return flt(bom_allowance_percentage)

	settings = frappe.get_doc("Inventory Tools Settings", {"company": company})
	if settings:
		settings_allowance_percentage = flt(settings.overproduction_percentage_for_work_order)
	else:
		settings_allowance_percentage = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
		)
	return settings_allowance_percentage
