# Copyright (c) 2023, AgriTheory and Contributors
# See license.txt

import datetime
import json

import frappe
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	check_if_return_invoice_linked_with_payment_entry,
	unlink_inter_company_doc,
	update_linked_doc,
)
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from frappe import _
from frappe.utils.data import cint

from inventory_tools.inventory_tools.overrides.landed_costing import update_valuation_rate


class InventoryToolsPurchaseInvoice(PurchaseInvoice):
	def validate_with_previous_doc(self):
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
		if not self.is_inline_lc_enabled():
			return super().on_submit()
		else:
			self.on_submit_parent_with_lc_changes()

	def on_cancel(self):
		if self.is_work_order_subcontracting_enabled() and self.is_subcontracted:
			self.on_cancel_revert_se_paid_qty()
		if not self.is_inline_lc_enabled():
			return super().on_cancel()
		else:
			self.on_cancel_parent_with_lc_changes()

	def is_work_order_subcontracting_enabled(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		return bool(settings and settings.enable_work_order_subcontracting)

	def is_inline_lc_enabled(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		return bool(settings and settings.enable_inline_landed_costing)

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

	def on_submit_parent_with_lc_changes(self):
		"""
		Function is a copy/modification of ERPNext's PurchaseInvoice on_submit class function (to
		accommodate the Inline Landed Costing feature changes) and why super calls the current
		class's parent
		"""
		super(PurchaseInvoice, self).on_submit()

		self.check_prev_docstatus()
		self.update_status_updater_args()
		self.update_prevdoc_status()

		frappe.get_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total
		)

		if not self.is_return:
			self.update_against_document_in_jv()
			self.update_billing_status_for_zero_amount_refdoc("Purchase Receipt")
			self.update_billing_status_for_zero_amount_refdoc("Purchase Order")

		self.update_billing_status_in_pr()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating ordered qty in bin depends upon updated ordered qty in PO
		if self.update_stock == 1:
			self.update_stock_ledger()

			if self.is_old_subcontracting_flow:
				self.set_consumed_qty_in_subcontract_order()

			from erpnext.stock.doctype.serial_no.serial_no import update_serial_nos_after_submit

			update_serial_nos_after_submit(self, "items")

		# CUSTOM CODE START
		# There are additional landed costs to update item valuations, but 'Update Stock' is unchecked
		#    (because items were received via Purchase Receipts)
		# Collect unique purchase receipt names from items (in case more than one PR covered by PI)
		prs = {item.purchase_receipt for item in self.get("items") if item.purchase_receipt}
		if (
			(not self.update_stock)
			and prs
			and (self.distribute_charges_based_on != "Don't Distribute")
			and (self.total_taxes_and_charges)
		):
			self.update_landed_cost(prs)
		# CUSTOM CODE END

		# this sequence because outstanding may get -negative
		self.make_gl_entries()

		if self.update_stock == 1:
			self.repost_future_sle_and_gle()

		if (
			frappe.db.get_single_value("Buying Settings", "project_update_frequency") == "Each Transaction"
		):
			self.update_project()

		update_linked_doc(self.doctype, self.name, self.inter_company_invoice_reference)
		self.update_advance_tax_references()

		self.process_common_party_accounting()

	def on_cancel_revert_se_paid_qty(self):
		# Reduces the Stock Entry Detail item's paid_qty by the to_pay_qty amount in the invoice
		for ste in self.get("subcontracting"):
			cur_paid = frappe.db.get_value("Stock Entry Detail", ste.se_detail_name, "paid_qty")
			frappe.db.set_value(
				"Stock Entry Detail", ste.se_detail_name, "paid_qty", cur_paid - ste.to_pay_qty
			)

	def on_cancel_parent_with_lc_changes(self):
		"""
		Function is a copy/modification of ERPNext's PurchaseInvoice on_cancel class function (to
		accommodate the Inline Landed Costing feature changes) and why super calls the current
		class's parent
		"""
		check_if_return_invoice_linked_with_payment_entry(self)

		super(PurchaseInvoice, self).on_cancel()

		self.check_on_hold_or_closed_status()

		self.update_status_updater_args()
		self.update_prevdoc_status()

		if not self.is_return:
			self.update_billing_status_for_zero_amount_refdoc("Purchase Receipt")
			self.update_billing_status_for_zero_amount_refdoc("Purchase Order")

		self.update_billing_status_in_pr()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating ordered qty in bin depends upon updated ordered qty in PO
		if self.update_stock == 1:
			self.update_stock_ledger()
			self.delete_auto_created_batches()

			if self.is_old_subcontracting_flow:
				self.set_consumed_qty_in_subcontract_order()

		# CUSTOM CODE START
		prs = {item.purchase_receipt for item in self.get("items") if item.purchase_receipt}
		if (
			(not self.update_stock)
			and prs
			and (self.distribute_charges_based_on != "Don't Distribute")
			and (self.total_taxes_and_charges)
		):
			self.update_landed_cost(prs, on_cancel=True)
		# CUSTOM CODE END

		self.make_gl_entries_on_cancel()

		if self.update_stock == 1:
			self.repost_future_sle_and_gle()

		if (
			frappe.db.get_single_value("Buying Settings", "project_update_frequency") == "Each Transaction"
		):
			self.update_project()
		self.db_set("status", "Cancelled")

		unlink_inter_company_doc(self.doctype, self.name, self.inter_company_invoice_reference)
		self.ignore_linked_doctypes = (
			"GL Entry",
			"Stock Ledger Entry",
			"Repost Item Valuation",
			"Repost Payment Ledger",
			"Repost Payment Ledger Items",
			"Repost Accounting Ledger",
			"Repost Accounting Ledger Items",
			"Unreconcile Payment",
			"Unreconcile Payment Entries",
			"Payment Ledger Entry",
			"Tax Withheld Vouchers",
		)
		self.update_advance_tax_references(cancel=1)

	def update_valuation_rate(self, reset_outgoing_rate=True):
		if self.is_inline_lc_enabled():
			update_valuation_rate(self, reset_outgoing_rate)
		else:
			super().update_valuation_rate(reset_outgoing_rate)

	def update_landed_cost(self, prs, on_cancel=False):
		"""
		Function is a copy/modification of ERPNext's LandedCostVoucher update_landed_cost class
		function (to accommodate the Inline Landed Costing feature changes). Adds landed costs to
		underlying Purchase Receipts.
		"""
		# Create a lookup dictionary by PR and item code to tax amount (field used to save LC/item): {PR_name: {item_code: item.item_tax_amount}}
		lc_per_item_dict = {pr: {} for pr in prs}
		for item in self.get("items"):
			if item.purchase_receipt:
				lc_per_item_dict[item.purchase_receipt][item.item_code] = item.item_tax_amount

		# Save LC/item into each PR item, update item valuation rate, update database
		for pr in prs:
			doc = frappe.get_doc("Purchase Receipt", pr)
			# Set (on_submit) or remove (on_cancel) landed_cost_voucher_amount in item
			for item in doc.get("items"):
				lcvamt = lc_per_item_dict[pr][item.item_code]
				if not on_cancel:
					item.landed_cost_voucher_amount = lc_per_item_dict[pr][item.item_code]
				else:
					item.landed_cost_voucher_amount = 0.0

			doc.update_valuation_rate(reset_outgoing_rate=False)

			for item in doc.get("items"):
				item.db_update()

			# asset rate will be updated while creating asset gl entries from PI or PY

			# update latest valuation rate in serial no
			self.update_rate_in_serial_no_for_non_asset_items(doc)

		# Store landed cost charges in GL dict for PR
		lc_from_pi = self.get_pr_lc_gl_entries(prs, on_cancel=on_cancel)

		# Update stock ledger and GL entries
		for pr in prs:
			# Replicate LCV flow
			doc = frappe.get_doc("Purchase Receipt", pr)
			# update stock & gl entries for cancelled state of PR
			doc.docstatus = 2
			doc.update_stock_ledger(
				allow_negative_stock=True, via_landed_cost_voucher=False
			)  # In buying_controller.py, ultimately calls make_sl_entries in stock_ledger.py
			doc.make_gl_entries_on_cancel()

			# update stock & gl entries for submit state of PR
			doc.docstatus = 1
			doc.update_stock_ledger(allow_negative_stock=True, via_landed_cost_voucher=False)
			doc.make_gl_entries(lc_from_pi=lc_from_pi[pr])
			doc.repost_future_sle_and_gle()

	def get_pr_lc_gl_entries(self, prs, on_cancel=False):
		"""
		Builds dict to hold GL-formatted entries for the landed costs to pass along to PR to
		properly capture tax account credit(s) against the debit to Stock on Hand

		:param pr_dict: dict, holds names of purchase receipt documents covered by invoice
		return: dict, formatted as follows:

		{
		    pr1_name: {lc_gl_format},
		    pr2_name: {lc_gl_format}
		}

		Where lc_gl_format matches what's returned by PR's get_item_account_wise_additional_cost:
		{
		    ('item code', 'item name'): {'Account for LC charges': {'amount': 10.0, 'base_amount': 10.0}}
		}
		amount and base_amount per item is prorated for each account used in the taxes table

		Example:
		{'PREC-RET-10000': {('6201', '6f89743482'): {'Expenses Included In Valuation - *': {'amount': 10.0, 'base_amount': 10.0}}}}
		"""
		if on_cancel:
			return {pr: {} for pr in prs}

		lc_from_pi = {}
		based_on_field = frappe.scrub(self.distribute_charges_based_on)

		# Collect total Amount or Qty from PI to prorate LC charges by account head (if multiple) by PR
		total_item_cost = sum(
			item.get(based_on_field) for item in self.get("items") if item.item_tax_amount
		)

		for pr in prs:
			doc = frappe.get_doc("Purchase Receipt", pr)
			item_account_wise_cost = {}

			for item in doc.items:  # Loop over PR items but then PI taxes
				if not item.landed_cost_voucher_amount:
					continue

				for account in self.taxes:
					# For each tax account in PI taxes, allocate same ratio as how total LCs were split by item
					item_account_wise_cost.setdefault((item.item_code, item.name), {})
					item_account_wise_cost[(item.item_code, item.name)].setdefault(
						account.account_head, {"amount": 0.0, "base_amount": 0.0}
					)

					item_account_wise_cost[(item.item_code, item.name)][account.account_head]["amount"] += (
						account.tax_amount_after_discount_amount * item.get(based_on_field) / total_item_cost
					)

					item_account_wise_cost[(item.item_code, item.name)][account.account_head]["base_amount"] += (
						account.base_tax_amount_after_discount_amount * item.get(based_on_field) / total_item_cost
					)

			lc_from_pi[pr] = item_account_wise_cost

		return lc_from_pi

	def update_rate_in_serial_no_for_non_asset_items(self, receipt_document):
		"""
		Function copied from LandedCostVoucher class in landed_cost_voucher.py to accommodate
		inline landed costs in a Purchase Invoice
		"""
		for item in receipt_document.get("items"):
			if not item.is_fixed_asset and item.serial_no:
				serial_nos = get_serial_nos(item.serial_no)
				if serial_nos:
					frappe.db.sql(
						"update `tabSerial No` set purchase_rate=%s where name in ({})".format(
							", ".join(["%s"] * len(serial_nos))
						),
						tuple([item.valuation_rate] + serial_nos),
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
