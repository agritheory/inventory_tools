# Copyright (c) 2023, AgriTheory and Contributors
# See license.txt

import datetime

import frappe
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from frappe import _
from frappe.utils.data import cint


class InventoryToolsPurchaseInvoice(PurchaseInvoice):
	def validate_with_previous_doc(self):
		"""
		HASH: 183ac4155046dc5d18f9a28c560b7586c5f12b4b
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/accounts/doctype/purchase_invoice/purchase_invoice.py
		METHOD: validate_with_previous_doc
		"""

		config = {
			"Purchase Order": {
				"ref_dn_field": "purchase_order",
				"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
			},
			"Purchase Order Item": {
				"ref_dn_field": "po_detail",
				"compare_fields": [["project", "="], ["item_code", "="], ["uom", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True,
			},
			"Purchase Receipt": {
				"ref_dn_field": "purchase_receipt",
				"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
			},
			"Purchase Receipt Item": {
				"ref_dn_field": "pr_detail",
				"compare_fields": [["project", "="], ["item_code", "="], ["uom", "="]],
				"is_child_table": True,
			},
		}

		pos = list({r.purchase_order for r in self.items})
		if len(pos) == 1 and frappe.get_value("Purchase Order", pos[0], "multi_company_purchase_order"):
			config["Purchase Order"]["compare_fields"] = [["currency", "="]]

		super(PurchaseInvoice, self).validate_with_previous_doc(config)

		if (
			cint(frappe.get_cached_value("Buying Settings", "None", "maintain_same_rate"))
			and not self.is_return
			and not self.is_internal_supplier
		):
			self.validate_rate_with_reference_doc(
				[
					["Purchase Order", "purchase_order", "po_detail"],
					["Purchase Receipt", "purchase_receipt", "pr_detail"],
				]
			)

	def validate(self):
		if self.is_work_order_subcontracting_enabled() and self.is_subcontracted:
			if not self.supplier_warehouse:
				self.supplier_warehouse = fetch_supplier_warehouse(self.company, self.supplier)
			self.validate_subcontracting_to_pay_qty()
		return super().validate()

	def on_submit(self):
		if self.is_work_order_subcontracting_enabled() and self.is_subcontracted:
			self.on_submit_save_se_paid_qty()
		return super().on_submit()

	def on_cancel(self):
		if self.is_work_order_subcontracting_enabled() and self.is_subcontracted:
			self.on_cancel_revert_se_paid_qty()
		return super().on_cancel()

	def is_work_order_subcontracting_enabled(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		return bool(settings and settings.enable_work_order_subcontracting)

	def validate_subcontracting_to_pay_qty(self):
		# Checks the qty the invoice will cover is not more than the outstanding qty
		for subc in self.get("subcontracting"):
			if subc.to_pay_qty > (subc.qty - subc.paid_qty):
				frappe.throw(
					_(
						f"The To Pay Qty in Subcontracting Detail row {subc.idx} cannot be more than Total Qty less the already Paid Qty."
					)
				)

	def on_submit_save_se_paid_qty(self):
		# Saves the invoiced quantity for the Stock Entry Detail row into paid_qty field
		for ste in self.get("subcontracting"):
			frappe.db.set_value(
				"Stock Entry Detail", ste.se_detail_name, "paid_qty", ste.paid_qty + ste.to_pay_qty
			)

	def on_cancel_revert_se_paid_qty(self):
		# Reduces the Stock Entry Detail item's paid_qty by the to_pay_qty amount in the invoice
		for ste in self.get("subcontracting"):
			cur_paid = frappe.db.get_value("Stock Entry Detail", ste.se_detail_name, "paid_qty")
			frappe.db.set_value(
				"Stock Entry Detail", ste.se_detail_name, "paid_qty", cur_paid - ste.to_pay_qty
			)


@frappe.whitelist()
def get_stock_entries(purchase_orders, from_date=None, to_date=None):
	# # Commented code is useful if having PO and attaching WOs to them is enforced
	# if isinstance(purchase_orders, str):
	# 	purchase_orders = json.loads(purchase_orders)

	if not from_date:
		from_date = datetime.date(1900, 1, 1)

	if not to_date:
		to_date = datetime.date(2100, 12, 31)

	# work_orders, fg_items = [], set()
	# for po in purchase_orders:
	# 	work_orders.extend(
	# 		frappe.get_all(
	# 			"Purchase Order Subcontracting Detail",
	# 			fields="work_order",
	# 			filters={"parent": po},
	# 			pluck="work_order"
	# 		)
	# 	)
	# 	for item in frappe.get_doc("Purchase Order", po).get("items"):
	# 		fg_items.add(item.get("fg_item"))

	stock_entry = frappe.qb.DocType("Stock Entry")
	se_detail = frappe.qb.DocType("Stock Entry Detail")
	po_sub = frappe.qb.DocType("Purchase Order Subcontracting Detail")
	po = frappe.qb.DocType("Purchase Order")
	item = frappe.qb.DocType("Item")

	query = (
		frappe.qb.from_(stock_entry)
		.inner_join(se_detail)
		.on(stock_entry.name == se_detail.parent)
		.left_join(po_sub)
		.on(stock_entry.work_order == po_sub.work_order)
		.left_join(item)
		.on(se_detail.item_code == item.item_code)
		.left_join(po)
		.on(po_sub.parent == po.name)
		.select(
			stock_entry.work_order,
			(stock_entry.name).as_("stock_entry"),
			(se_detail.name).as_("se_detail_name"),
			(po_sub.parent).as_("purchase_order"),
			se_detail.item_code,
			se_detail.item_name,
			se_detail.qty,
			se_detail.transfer_qty,
			se_detail.uom,
			se_detail.stock_uom,
			se_detail.conversion_factor,
			se_detail.valuation_rate,
			se_detail.paid_qty,
		)
		.where(stock_entry.docstatus == 1)
		.where(stock_entry.stock_entry_type == "Manufacture")
		.where(stock_entry.posting_date >= from_date)
		.where(stock_entry.posting_date <= to_date)
		# .where(stock_entry.work_order.isin(work_orders))
		# .where(se_detail.item_code.isin(fg_items))
		.where(se_detail.is_finished_item == 1)
		.where(se_detail.paid_qty < se_detail.qty)
		.where(item.is_sub_contracted_item == 1)
		.where(po.docstatus != 2)
	)

	return frappe.db.sql(
		query.get_sql(),
		{
			"from_date": from_date,
			"to_date": to_date,
			# "work_orders": work_orders,
			# "fg_items": fg_items,
		},
		as_dict=1,
	)


@frappe.whitelist()
def fetch_supplier_warehouse(company, supplier):
	return frappe.db.get_value(
		"Subcontracting Default",
		{"parent": supplier, "company": company},
		["return_warehouse"],
	)
