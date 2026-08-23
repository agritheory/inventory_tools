# Copyright (c) 2023, AgriTheory and Contributors
# See license.txt

import json
import types

import frappe
from erpnext import get_default_cost_center
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	make_inter_company_purchase_invoice,
)
from erpnext.accounts.party import get_party_account
from erpnext.buying.doctype.purchase_order.purchase_order import (
	PurchaseOrder,
	make_purchase_invoice,
	make_purchase_receipt,
)
from erpnext.controllers.accounts_controller import (
	get_default_taxes_and_charges,
	force_item_fields,
)
from erpnext.stock.doctype.item.item import get_uom_conv_factor
from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company
from frappe import _, throw
from frappe.utils import cint, flt


def skip_bound_method(*args, **kwargs):
	return


def resolve_purchase_order_item_company(item):
	"""Return the company that should receive this PO line (Material Request company)."""
	if item.get("company"):
		return item.company
	if item.get("material_request"):
		company = frappe.get_value("Material Request", item.material_request, "company")
		if company:
			return company
	if item.get("warehouse"):
		return frappe.get_value("Warehouse", item.warehouse, "company")
	return None


def normalize_selected_row_names(rows):
	rows = json.loads(rows) if isinstance(rows, str) else rows
	names = set()
	for row in rows or []:
		if isinstance(row, str):
			names.add(row)
		elif isinstance(row, dict) and row.get("name"):
			names.add(row["name"])
	return names


def group_po_items_by_requesting_company(po, selected_names):
	forwarding = frappe._dict()
	for row in po.items:
		if row.name not in selected_names:
			continue
		company = resolve_purchase_order_item_company(row)
		if company in forwarding:
			forwarding[company].append(row.name)
		else:
			forwarding[company] = [row.name]
	return forwarding


def multi_company_receipt_applies_putaway_rule(company):
	return cint(
		frappe.db.get_value(
			"Inventory Tools Settings",
			company,
			"apply_putaway_rule_on_multi_company_receipt",
		)
	)


def apply_requesting_company_to_purchase_receipt(pr, po, company):
	pr.company = company
	if company != po.company:
		pr.credit_to = get_party_account("Supplier", po.supplier, company)
	company_cost_center = frappe.get_value("Company", company, "cost_center")
	for item in pr.items:
		item.cost_center = company_cost_center
	if multi_company_receipt_applies_putaway_rule(company):
		pr.apply_putaway_rule = 1
	pr.run_method("set_missing_values")
	pr.run_method("calculate_taxes_and_totals")


def apply_requesting_company_to_purchase_invoice(pi, po, company):
	pi.company = company
	pi.credit_to = get_party_account("Supplier", po.supplier, company)
	company_cost_center = frappe.get_value("Company", company, "cost_center")
	for item in pi.items:
		item.cost_center = company_cost_center
	pi.run_method("set_missing_values")
	pi.run_method("calculate_taxes_and_totals")


def build_purchase_receipt_for_company(po_name, company, po_item_names):
	po = frappe.get_doc("Purchase Order", po_name)
	pr = make_purchase_receipt(po_name, args={"filtered_children": po_item_names})
	apply_requesting_company_to_purchase_receipt(pr, po, company)
	return pr


def build_purchase_invoice_for_company(po_name, company, po_item_names):
	po = frappe.get_doc("Purchase Order", po_name)
	pi = make_purchase_invoice(po_name, args={"filtered_children": po_item_names})
	apply_requesting_company_to_purchase_invoice(pi, po, company)
	return pi


class InventoryToolsPurchaseOrder(PurchaseOrder):
	def validate_with_previous_doc(self):
		"""
		HASH: 8f811728d97293744bb35f6a3bdba889708127c5
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
		warehouses = list({d.warehouse for d in self.get("items") if getattr(d, "warehouse", None)})

		warehouses.extend(
			list({d.target_warehouse for d in self.get("items") if getattr(d, "target_warehouse", None)})
		)

		warehouses.extend(
			list({d.from_warehouse for d in self.get("items") if getattr(d, "from_warehouse", None)})
		)

		for w in warehouses:
			validate_disabled_warehouse(w)
			if not self.multi_company_purchase_order:
				validate_warehouse_company(w, self.company)

	def validate(self):
		if self.multi_company_purchase_order:
			for item in self.items:
				item.company = resolve_purchase_order_item_company(item)

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

	def set_missing_item_details(self, for_validate=False):
		"""
		HASH: baa6d2bcdca633d60bfb596fc76df5cc5ab8b8fd
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/controllers/accounts_controller.py
		METHOD: set_missing_item_details
		"""
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		if hasattr(self, "items"):
			parent_dict = {}
			for fieldname in self.meta.get_valid_columns():
				parent_dict[fieldname] = self.get(fieldname)

			if self.doctype in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
				document_type = f"{self.doctype} Item"
				parent_dict.update({"document_type": document_type})

			# party_name field used for customer in quotation
			if (
				self.doctype == "Quotation"
				and self.quotation_to == "Customer"
				and parent_dict.get("party_name")
			):
				parent_dict.update({"customer": parent_dict.get("party_name")})

			self.pricing_rules = []

			for item in self.get("items"):
				if item.get("item_code"):
					args = parent_dict.copy()
					args.update(item.as_dict())
					# Item custom field "company" (Requesting Company) must not replace PO company.
					args["company"] = self.company

					args["doctype"] = self.doctype
					args["name"] = self.name
					args["child_doctype"] = item.doctype
					args["child_docname"] = item.name
					args["ignore_pricing_rule"] = (
						self.ignore_pricing_rule if hasattr(self, "ignore_pricing_rule") else 0
					)

					if not args.get("transaction_date"):
						args["transaction_date"] = args.get("posting_date")

					if self.get("is_subcontracted"):
						args["is_subcontracted"] = self.is_subcontracted

					# CUSTOM CODE START (uses overridden function defined below)
					ret = get_item_details(args, self, for_validate=for_validate, overwrite_warehouse=False)
					# CUSTOM CODE END
					for fieldname, value in ret.items():
						if item.meta.get_field(fieldname) and value is not None:
							if (
								item.get(fieldname) is None
								or fieldname in force_item_fields
								or (fieldname in ["serial_no", "batch_no"] and item.get("use_serial_batch_fields"))
							):
								item.set(fieldname, value)

							elif fieldname in ["cost_center", "conversion_factor"] and not item.get(fieldname):
								item.set(fieldname, value)
							elif fieldname == "item_tax_rate" and not (
								self.get("is_return") and self.get("return_against")
							):
								item.set(fieldname, value)
							elif fieldname == "serial_no":
								# Ensure that serial numbers are matched against Stock UOM
								item_conversion_factor = item.get("conversion_factor") or 1.0
								item_qty = abs(item.get("qty")) * item_conversion_factor

								if item_qty != len(get_serial_nos(item.get("serial_no"))):
									item.set(fieldname, value)

							elif (
								ret.get("pricing_rule_removed")
								and value is not None
								and fieldname
								in [
									"discount_percentage",
									"discount_amount",
									"rate",
									"margin_rate_or_amount",
									"margin_type",
									"remove_free_item",
								]
							):
								# reset pricing rule fields if pricing_rule_removed
								item.set(fieldname, value)

					if self.doctype in ["Purchase Invoice", "Sales Invoice"] and item.meta.get_field(
						"is_fixed_asset"
					):
						item.set("is_fixed_asset", ret.get("is_fixed_asset", 0))

					# Double check for cost center
					# Items add via promotional scheme may not have cost center set
					if hasattr(item, "cost_center") and not item.get("cost_center"):
						item.set(
							"cost_center",
							self.get("cost_center") or get_default_cost_center(self.company),
						)

					if ret.get("pricing_rules"):
						self.apply_pricing_rule_on_items(item, ret)
						self.set_pricing_rule_details(item, ret)
				else:
					# Transactions line item without item code

					uom = item.get("uom")
					stock_uom = item.get("stock_uom")
					if bool(uom) != bool(stock_uom):  # xor
						item.stock_uom = item.uom = uom or stock_uom

					# UOM cannot be zero so substitute as 1
					item.conversion_factor = (
						get_uom_conv_factor(item.get("uom"), item.get("stock_uom"))
						or item.get("conversion_factor")
						or 1
					)

			if self.doctype == "Purchase Invoice":
				self.set_expense_account(for_validate)


@frappe.whitelist()
def get_multi_company_po_receipt_rows(docname: str) -> list[dict]:
	"""Rows for the multi-company Purchase Receipt dialog."""
	doc = frappe.get_doc("Purchase Order", docname)
	rows = []
	for item in doc.items:
		if flt(item.rate) == 0 or flt(item.stock_qty) <= 0:
			continue
		pending_qty = flt(item.qty) - flt(item.received_qty)
		if pending_qty <= 0:
			continue
		rows.append(
			{
				"name": item.name,
				"company": resolve_purchase_order_item_company(item),
				"warehouse": item.warehouse,
				"item_code": item.item_code,
				"qty": pending_qty,
				"material_request_item": item.material_request_item,
			}
		)
	return rows


@frappe.whitelist()
def make_purchase_invoices(docname: str, rows: list | str) -> list[str]:
	selected_names = normalize_selected_row_names(rows)
	doc = frappe.get_doc("Purchase Order", docname)
	created = []
	for company, po_item_names in group_po_items_by_requesting_company(doc, selected_names).items():
		pi = build_purchase_invoice_for_company(docname, company, po_item_names)
		pi.save()
		created.append(pi.name)
	return created


@frappe.whitelist()
def make_purchase_receipts(docname: str, rows: list | str) -> list[str]:
	selected_names = normalize_selected_row_names(rows)
	doc = frappe.get_doc("Purchase Order", docname)
	created = []
	for company, po_item_names in group_po_items_by_requesting_company(doc, selected_names).items():
		pr = build_purchase_receipt_for_company(docname, company, po_item_names)
		pr.save()
		created.append(pr.name)
	return created


@frappe.whitelist()
def make_sales_invoices(docname: str, rows: list | str) -> None:
	selected_names = normalize_selected_row_names(rows)
	doc = frappe.get_doc("Purchase Order", docname)
	buying_settings = frappe.get_doc("Buying Settings", "Buying Settings")
	forwarding = frappe._dict()

	for row in doc.items:
		if row.name in selected_names:
			company = resolve_purchase_order_item_company(row)
			if company in forwarding:
				forwarding[company].append(row.name)
			else:
				forwarding[company] = [row.name]

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
		si.set_total_in_words = types.MethodType(skip_bound_method, si)
		si.set_payment_schedule = types.MethodType(skip_bound_method, si)
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
	HASH: 41effcf7543095575cec7ff7b66ee06113882253
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
	HASH: af21bca2318089bfee543fdf2180e9d55c7f2833
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
