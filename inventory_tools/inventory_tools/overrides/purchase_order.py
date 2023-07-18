# Copyright (c) 2023, AgriTheory and Contributors
# See license.txt

import json
import types

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


def _bypass(*args, **kwargs):
	return


class InventoryToolsPurchaseOrder(PurchaseOrder):
	def validate_with_previous_doc(self):
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
		from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company

		warehouses = list({d.warehouse for d in self.get("items") if getattr(d, "warehouse", None)})

		target_warehouses = list(
			{d.target_warehouse for d in self.get("items") if getattr(d, "target_warehouse", None)}
		)

		warehouses.extend(target_warehouses)

		from_warehouse = list(
			{d.from_warehouse for d in self.get("items") if getattr(d, "from_warehouse", None)}
		)

		warehouses.extend(from_warehouse)

		for w in warehouses:
			validate_disabled_warehouse(w)
			if not self.multi_company_purchase_order:
				validate_warehouse_company(w, self.company)


@frappe.whitelist()
def make_purchase_invoices(docname: str, rows: list) -> None:
	rows = json.loads(rows) if isinstance(rows, str) else rows
	doc = frappe.get_doc("Purchase Order", docname)
	forwarding = frappe._dict()
	for row in doc.items:
		if row.name in rows:
			if row.company in forwarding:
				forwarding[row.company].append(row.name)
			else:
				forwarding[row.company] = [row.name]

	for company, rows in forwarding.items():
		pi = make_purchase_invoice(docname)
		pi.company = company
		pi.credit_to = frappe.get_value("Company", pi.company, "default_payable_account")
		for row in pi.items:
			if row.po_detail in rows:
				continue
			else:
				pi.items.remove(row)
		pi.save()


@frappe.whitelist()
def make_purchase_receipts(docname: str, rows: list) -> None:
	rows = json.loads(rows) if isinstance(rows, str) else rows
	doc = frappe.get_doc("Purchase Order", docname)
	forwarding = frappe._dict()
	for row in doc.items:
		if row.name in rows:
			if row.company in forwarding:
				forwarding[row.company].append(row.name)
			else:
				forwarding[row.company] = [row.name]

	for company, rows in forwarding.items():
		pr = make_purchase_receipt(docname)
		pr.company = company
		for row in pr.items:
			if row.purchase_order_item in rows:
				continue
			else:
				pr.items.remove(row)
		pr.save()


@frappe.whitelist()
def make_sales_invoices(docname: str, rows: list) -> None:
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
		print(taxes_and_charges)
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
