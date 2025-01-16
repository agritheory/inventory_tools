# Copyright (c) 2023, AgriTheory and Contributors
# See license.txt

import json
import types
from typing import Union

import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	make_inter_company_purchase_invoice,
)
from erpnext.buying.doctype.purchase_order.purchase_order import (
	PurchaseOrder,
	make_purchase_invoice,
	make_purchase_receipt,
)
from erpnext.controllers.accounts_controller import get_default_taxes_and_charges
from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company
from frappe import _, throw


def _bypass(*args, **kwargs):
	return


class InventoryToolsPurchaseOrder(PurchaseOrder):
	def validate_with_previous_doc(self):
		"""
		HASH: f833923f2fcc5ce18847a93fe741db7e59a4d349
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/buying/doctype/purchase_order/purchase_order.py
		METHOD: validate_with_previous_doc
		"""
		config = {
			"Supplier Quotation": {
				"ref_dn_field": "supplier_quotation",
				"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
			},
			"Supplier Quotation Item": {
				"ref_dn_field": "supplier_quotation_item",
				"compare_fields": [
					["project", "="],
					["item_code", "="],
					["uom", "="],
					["conversion_factor", "="],
				],
				"is_child_table": True,
			},
			"Material Request": {
				"ref_dn_field": "material_request",
				"compare_fields": [["company", "="]],
			},
			"Material Request Item": {
				"ref_dn_field": "material_request_item",
				"compare_fields": [["project", "="], ["item_code", "="]],
				"is_child_table": True,
			},
		}
		if self.multi_company_purchase_order:
			config.pop("Material Request")
		super(PurchaseOrder, self).validate_with_previous_doc(config)

	def validate_warehouse(self):
		warehouses = []
		inventory_tools_settings = frappe.get_doc("Inventory Tools Settings", self.company)

		for d in self.get("items"):
			if (
				self.multi_company_purchase_order
				and not inventory_tools_settings.aggregated_purchasing_warehouse
			):
				validate_warehouse_company(d.warehouse, d.material_request_company)
				continue
			if getattr(d, "warehouse", None):
				warehouses.append(d.warehouse)
			if getattr(d, "target_warehouse", None):
				warehouses.append(d.warehouse)
			if getattr(d, "from_warehouse", None):
				warehouses.append(d.warehouse)

		for w in warehouses:
			validate_disabled_warehouse(w)
			if not self.multi_company_purchase_order:
				validate_warehouse_company(w, self.company)

	def validate(self):
		if self.is_work_order_subcontracting_enabled() and self.is_subcontracted:
			self.validate_subcontracting_fg_qty()
			for row in self.subcontracting:
				# TODO: set work order supplier to empty string in on_cancel
				frappe.set_value("Work Order", row.work_order, "supplier", self.supplier)

		super().validate()

	def is_work_order_subcontracting_enabled(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		return bool(settings and settings.enable_work_order_subcontracting)

	def validate_subcontracting_fg_qty(self):
		sub_wo = self.get("subcontracting")
		if sub_wo:
			items_fg_qty = sum(item.get("fg_item_qty") or 0 for item in self.get("items"))
			subc_fg_qty = sum(row.get("fg_item_qty") or 0 for row in sub_wo)
			# Check that the item finished good qty and the subcontracting qty are within the item's stock_qty field's precision number of decimals
			precision = int(frappe.get_precision("Purchase Order Item", "stock_qty"))
			diff = abs(items_fg_qty - subc_fg_qty)
			if diff > (1 / (10**precision)):
				frappe.msgprint(  # Just a warning in the case: PO is created before WO's exist, several WOs needed to complete the work (each one has less than PO)
					msg=_(
						f"The total of Finished Good Item Qty for all items does not match the total Finished Good Item Qty in the Subcontracting table. There is a difference of {diff}."
					),
					title=_("Warning"),
					indicator="red",
				)


@frappe.whitelist()
def make_purchase_invoices(docname: str, rows: Union[list, str]) -> None:
	rows = json.loads(rows) if isinstance(rows, str) else rows
	doc = frappe.get_doc("Purchase Order", docname)
	inventory_tools_settings = frappe.get_doc("Inventory Tools Settings", doc.company)
	forwarding = frappe._dict()
	for row_name in rows:
		for row in doc.items:
			if row_name == row.name:
				company = frappe.get_value("Material Request", row.material_request, "company")
				if company in forwarding:
					forwarding[company].append(row.name)
				else:
					forwarding[company] = [row.name]

	for company, _rows in forwarding.items():
		pi = make_purchase_invoice(docname)
		pi.company = company
		pi.credit_to = frappe.get_value("Company", pi.company, "default_payable_account")
		filtered_rows = []
		for row in pi.items:
			if row.po_detail in _rows:
				if inventory_tools_settings.aggregated_purchasing_warehouse is not None:
					row.warehouse = inventory_tools_settings.aggregated_purchasing_warehouse
				else:
					material_request_item = frappe.get_value(
						"Purchase Order Item", row.po_detail, "material_request_item"
					)
					warehouse, cost_center = frappe.get_value(
						"Material Request Item", material_request_item, ["warehouse", "cost_center"]
					)
					row.warehouse = warehouse
					row.cost_center = cost_center
				filtered_rows.append(row)
		pi.items = filtered_rows
		pi.save()


@frappe.whitelist()
def make_purchase_receipts(docname: str, rows: Union[list, str]) -> None:
	rows = json.loads(rows) if isinstance(rows, str) else rows
	doc = frappe.get_doc("Purchase Order", docname)
	inventory_tools_settings = frappe.get_doc("Inventory Tools Settings", doc.company)

	forwarding = frappe._dict()
	for row_name in rows:
		for row in doc.items:
			if row_name == row.name:
				company = frappe.get_value("Material Request", row.material_request, "company")
				if company in forwarding:
					forwarding[company].append(row.name)
				else:
					forwarding[company] = [row.name]

	for company, _rows in forwarding.items():
		pr = make_purchase_receipt(docname)
		pr.company = company
		filtered_rows = []
		for row in pr.items:
			if row.purchase_order_item in _rows:
				if inventory_tools_settings.aggregated_purchasing_warehouse is not None:
					row.warehouse = inventory_tools_settings.aggregated_purchasing_warehouse
				else:
					warehouse, cost_center = frappe.get_value(
						"Material Request Item", row.material_request_item, ["warehouse", "cost_center"]
					)
					row.warehouse = warehouse
					row.cost_center = cost_center
				filtered_rows.append(row)
		pr.items = filtered_rows
		pr.save()


@frappe.whitelist()
def make_sales_invoices(docname: str, rows: Union[list, str]) -> None:
	rows = json.loads(rows) if isinstance(rows, str) else rows
	doc = frappe.get_doc("Purchase Order", docname)
	buying_settings = frappe.get_doc("Buying Settings", "Buying Settings")
	forwarding = frappe._dict()

	for row in doc.items:
		if row.name in rows:
			if row.company in forwarding:
				forwarding[row.company].append(row.name)
			else:
				forwarding[row.company] = [row.name]

	for company, rows in forwarding.items():
		si = frappe.new_doc("Sales Invoice")
		si.company = doc.company
		si.customer = company
		si.update_stock = 1
		si.selling_price_list = frappe.get_value("Price List", {"buying": 1, "selling": 1})
		for row in doc.items:
			if row.name not in rows:
				continue
			si.append(
				"items",
				{
					"item_code": row.item_code,
					"item_name": row.item_name,
					"item_description": row.description,
					"qty": row.qty,
					"uom": row.uom,
					"rate": row.rate,
					"purchase_order": doc.name,
					"warehouse": buying_settings.aggregated_purchasing_warehouse,
					"cost_center": frappe.get_value("Company", si.company, "cost_center"),
				},
			)
		taxes_and_charges = get_default_taxes_and_charges(
			"Sales Taxes and Charges Template", company=si.company
		)
		si.taxes_and_charges = taxes_and_charges.get("taxes_and_charges")
		for tax in taxes_and_charges.get("taxes"):
			si.append("taxes", tax)
		si.is_internal_supplier = 1
		si.bill_date = doc.schedule_date
		si.set_total_in_words = types.MethodType(_bypass, si)
		si.set_payment_schedule = types.MethodType(_bypass, si)
		si.title = f"Transfer {doc.supplier} to {si.customer}"
		si.save()

		pi = make_inter_company_purchase_invoice(si.name, None)
		pi.update_stock = 1
		for row in si.items:
			row.purchase_order = doc.name
			row.warehouse = buying_settings.aggregated_purchasing_warehouse
		pi.buying_price_list = si.selling_price_list
		taxes_and_charges = get_default_taxes_and_charges(
			"Purchase Taxes and Charges Template", company=pi.company
		)
		pi.taxes_and_charges = taxes_and_charges.get("taxes_and_charges")
		for tax in taxes_and_charges.get("taxes"):
			pi.append("taxes", tax)
		pi.is_internal_supplier = 1
		pi.inter_company_invoice_reference = si.name
		pi.title = f"Transfer {doc.supplier} to {pi.company}"
		pi.save()


@frappe.whitelist()
def get_item_details(args, doc=None, for_validate=False, overwrite_warehouse=True):
	"""
	HASH: 5c5349ed16680a22a8fd16a1f6f9ed16957069b4
	REPO: https://github.com/frappe/erpnext/
	PATH: erpnext/stock/get_item_details.py
	METHOD: get_item_details
	"""
	import erpnext.stock.get_item_details

	erpnext.stock.get_item_details.validate_item_details = validate_item_details
	out = erpnext.stock.get_item_details.get_item_details(
		args, doc, for_validate, overwrite_warehouse
	)
	return out


@frappe.whitelist()
def validate_item_details(args, item):
	"""
	HASH: 5c5349ed16680a22a8fd16a1f6f9ed16957069b4
	REPO: https://github.com/frappe/erpnext/
	PATH: erpnext/stock/get_item_details.py
	METHOD: validate_item_details
	"""
	if not args.company:
		throw(_("Please specify Company"))

	settings = frappe.get_doc("Inventory Tools Settings", {"company": args.company})

	from erpnext.stock.doctype.item.item import validate_end_of_life

	validate_end_of_life(item.name, item.end_of_life, item.disabled)

	if frappe.utils.cint(item.has_variants):
		msg = f"Item {item.name} is a template, please select one of its variants"

		throw(_(msg), title=_("Template Item Selected"))

	elif args.transaction_type == "buying" and args.doctype != "Material Request":
		if not (settings and settings.enable_work_order_subcontracting):
			if args.get("is_subcontracted"):
				if args.get("is_old_subcontracting_flow"):
					if item.is_sub_contracted_item != 1:
						throw(_("Item {0} must be a Sub-contracted Item").format(item.name))
				else:
					if item.is_stock_item:
						throw(_("Item {0} must be a Non-Stock Item").format(item.name))
