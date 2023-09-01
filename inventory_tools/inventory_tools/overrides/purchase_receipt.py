# Copyright (c) 2023, AgriTheory and Contributors
# See license.txt

import json

import erpnext
import frappe
from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from erpnext.accounts.utils import get_account_currency
from erpnext.stock import get_warehouse_account_map
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
from frappe.utils.data import cint, flt

from inventory_tools.inventory_tools.overrides.landed_costing import update_valuation_rate


class InventoryToolsPurchaseReceipt(PurchaseReceipt):
	def validate_with_previous_doc(self):
		config = {
			"Purchase Order": {
				"ref_dn_field": "purchase_order",
				"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
			},
			"Purchase Order Item": {
				"ref_dn_field": "purchase_order_item",
				"compare_fields": [["project", "="], ["uom", "="], ["item_code", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True,
			},
		}
		pos = list({r.purchase_order for r in self.items})
		if len(pos) == 1 and frappe.get_value("Purchase Order", pos[0], "multi_company_purchase_order"):
			config["Purchase Order"]["compare_fields"] = [["supplier", "="], ["currency", "="]]
		super(PurchaseReceipt, self).validate_with_previous_doc(config)

		if (
			cint(frappe.db.get_single_value("Buying Settings", "maintain_same_rate"))
			and not self.is_return
			and not self.is_internal_supplier
		):
			self.validate_rate_with_reference_doc(
				[["Purchase Order", "purchase_order", "purchase_order_item"]]
			)

	def is_work_order_subcontracting_enabled(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		return bool(settings and settings.enable_work_order_subcontracting)

	def is_inline_lc_enabled(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		return bool(settings and settings.enable_inline_landed_costing)

	def update_valuation_rate(self, reset_outgoing_rate=True):
		if self.is_inline_lc_enabled():
			update_valuation_rate(self, reset_outgoing_rate)
		else:
			super().update_valuation_rate(reset_outgoing_rate)

	def set_landed_cost_voucher_amount(self):
		"""
		Function modified from buying_controller.py to to accommodate inline landed costs
		        in a linked Purchase Invoice
		"""
		if not self.is_inline_lc_enabled():
			super().set_landed_cost_voucher_amount()
		else:
			print("IN OVERRIDES SET_LANDED_COST_VOUCHER_AMOUNT (FOR INLINE LANDED COSTING)")
			for d in self.get("items"):
				lc_voucher_data = frappe.db.sql(
					"""select sum(applicable_charges), cost_center
					from `tabLanded Cost Item`
					where docstatus = 1 and purchase_receipt_item = %s""",
					d.name,
				)
				# CUSTOM CODE START
				d.landed_cost_voucher_amount = (
					lc_voucher_data[0][0] if (lc_voucher_data and lc_voucher_data[0][0]) else 0.0
				)
				# CUSTOM CODE END
				if not d.cost_center and lc_voucher_data and lc_voucher_data[0][1]:
					d.db_set("cost_center", lc_voucher_data[0][1])

	def make_gl_entries(self, gl_entries=None, from_repost=False, lc_from_pi=None):
		"""
		Function copied/modified from stock_controller.py to accommodate revised
		        function signature
		New parameter lc_from_pi is None unless Enable Inline Landed Costing
		        feature is set and landed costs are included in a Purchase Invoice
		"""
		if self.docstatus == 2:
			make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

		provisional_accounting_for_non_stock_items = cint(
			frappe.get_cached_value(
				"Company", self.company, "enable_provisional_accounting_for_non_stock_items"
			)
		)

		if (
			cint(erpnext.is_perpetual_inventory_enabled(self.company))
			or provisional_accounting_for_non_stock_items
		):
			warehouse_account = get_warehouse_account_map(self.company)

			if self.docstatus == 1:
				if not gl_entries:
					# CUSTOM CODE START
					gl_entries = self.get_gl_entries(warehouse_account=warehouse_account, lc_from_pi=lc_from_pi)
					# CUSTOM CODE END
				make_gl_entries(gl_entries, from_repost=from_repost)

		elif self.doctype in ["Purchase Receipt", "Purchase Invoice"] and self.docstatus == 1:
			gl_entries = []
			gl_entries = self.get_asset_gl_entry(gl_entries)
			make_gl_entries(gl_entries, from_repost=from_repost)

	def get_gl_entries(self, warehouse_account=None, lc_from_pi=None):
		"""
		Function copied/modified from ERPNext's PurchaseReceipt class in purchase_receipt.py
		        to accommodate revised function signature
		New parameter lc_from_pi is None unless Enable Inline Landed Costing
		        feature is set and landed costs are included in a Purchase Invoice
		"""
		from erpnext.accounts.general_ledger import process_gl_map

		gl_entries = []

		# CUSTOM CODE START
		self.make_item_gl_entries(gl_entries, warehouse_account=warehouse_account, lc_from_pi=lc_from_pi)
		# CUSTOM CODE END
		self.make_tax_gl_entries(gl_entries)
		self.get_asset_gl_entry(gl_entries)

		return process_gl_map(gl_entries)

	def make_item_gl_entries(self, gl_entries, warehouse_account=None, lc_from_pi=None):
		"""
		Function copied/modified from ERPNext's PurchaseReceipt class in purchase_receipt.py
		        to accommodate revised function signature
		New parameter lc_from_pi is None unless Enable Inline Landed Costing
		        feature is set and landed costs are included in a Purchase Invoice
		"""
		from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import (
			get_purchase_document_details,
		)

		stock_rbnb = None
		if erpnext.is_perpetual_inventory_enabled(self.company):
			stock_rbnb = self.get_company_default("stock_received_but_not_billed")
			# CUSTOM CODE START
			landed_cost_entries = get_item_account_wise_additional_cost(self.name, lc_from_pi=lc_from_pi)
			# CUSTOM CODE END
			expenses_included_in_valuation = self.get_company_default("expenses_included_in_valuation")

		warehouse_with_no_account = []
		stock_items = self.get_stock_items()
		provisional_accounting_for_non_stock_items = cint(
			frappe.db.get_value(
				"Company", self.company, "enable_provisional_accounting_for_non_stock_items"
			)
		)

		exchange_rate_map, net_rate_map = get_purchase_document_details(self)  # new in v14

		for d in self.get("items"):
			if d.item_code in stock_items and flt(d.valuation_rate) and flt(d.qty):
				if warehouse_account.get(d.warehouse):
					stock_value_diff = frappe.db.get_value(
						"Stock Ledger Entry",
						{
							"voucher_type": "Purchase Receipt",
							"voucher_no": self.name,
							"voucher_detail_no": d.name,
							"warehouse": d.warehouse,
							"is_cancelled": 0,
						},
						"stock_value_difference",
					)

					warehouse_account_name = warehouse_account[d.warehouse]["account"]
					warehouse_account_currency = warehouse_account[d.warehouse]["account_currency"]
					supplier_warehouse_account = warehouse_account.get(self.supplier_warehouse, {}).get("account")
					supplier_warehouse_account_currency = warehouse_account.get(self.supplier_warehouse, {}).get(
						"account_currency"
					)
					remarks = self.get("remarks") or frappe._("Accounting Entry for Stock")

					# If PR is sub-contracted and fg item rate is zero
					# in that case if account for source and target warehouse are same,
					# then GL entries should not be posted
					if (
						flt(stock_value_diff) == flt(d.rm_supp_cost)
						and warehouse_account.get(self.supplier_warehouse)
						and warehouse_account_name == supplier_warehouse_account
					):
						continue

					self.add_gl_entry(
						gl_entries=gl_entries,
						account=warehouse_account_name,
						cost_center=d.cost_center,
						debit=stock_value_diff,
						credit=0.0,
						remarks=remarks,
						against_account=stock_rbnb,
						account_currency=warehouse_account_currency,
						item=d,
					)

					# GL Entry for from warehouse or Stock Received but not billed
					# Intentionally passed negative debit amount to avoid incorrect GL Entry validation
					credit_currency = (
						get_account_currency(warehouse_account[d.from_warehouse]["account"])
						if d.from_warehouse
						else get_account_currency(stock_rbnb)
					)

					credit_amount = (
						flt(d.base_net_amount, d.precision("base_net_amount"))
						if credit_currency == self.company_currency
						else flt(d.net_amount, d.precision("net_amount"))
					)

					outgoing_amount = d.base_net_amount
					if self.is_internal_transfer() and d.valuation_rate:
						outgoing_amount = abs(
							frappe.db.get_value(
								"Stock Ledger Entry",
								{
									"voucher_type": "Purchase Receipt",
									"voucher_no": self.name,
									"voucher_detail_no": d.name,
									"warehouse": d.from_warehouse,
									"is_cancelled": 0,
								},
								"stock_value_difference",
							)
						)
						credit_amount = outgoing_amount

					if credit_amount:
						account = warehouse_account[d.from_warehouse]["account"] if d.from_warehouse else stock_rbnb

						self.add_gl_entry(
							gl_entries=gl_entries,
							account=account,
							cost_center=d.cost_center,
							debit=-1 * flt(outgoing_amount, d.precision("base_net_amount")),
							credit=0.0,
							remarks=remarks,
							against_account=warehouse_account_name,
							debit_in_account_currency=-1 * credit_amount,
							account_currency=credit_currency,
							item=d,
						)

						# check if the exchange rate has changed
						if d.get("purchase_invoice"):
							if (
								exchange_rate_map[d.purchase_invoice]
								and self.conversion_rate != exchange_rate_map[d.purchase_invoice]
								and d.net_rate == net_rate_map[d.purchase_invoice_item]
							):

								discrepancy_caused_by_exchange_rate_difference = (d.qty * d.net_rate) * (
									exchange_rate_map[d.purchase_invoice] - self.conversion_rate
								)

								self.add_gl_entry(
									gl_entries=gl_entries,
									account=account,
									cost_center=d.cost_center,
									debit=0.0,
									credit=discrepancy_caused_by_exchange_rate_difference,
									remarks=remarks,
									against_account=self.supplier,
									debit_in_account_currency=-1 * discrepancy_caused_by_exchange_rate_difference,
									account_currency=credit_currency,
									item=d,
								)

								self.add_gl_entry(
									gl_entries=gl_entries,
									account=self.get_company_default("exchange_gain_loss_account"),
									cost_center=d.cost_center,
									debit=discrepancy_caused_by_exchange_rate_difference,
									credit=0.0,
									remarks=remarks,
									against_account=self.supplier,
									debit_in_account_currency=-1 * discrepancy_caused_by_exchange_rate_difference,
									account_currency=credit_currency,
									item=d,
								)

					# Amount added through landed-cost-voucher
					if d.landed_cost_voucher_amount and landed_cost_entries:
						for account, amount in landed_cost_entries[(d.item_code, d.name)].items():
							account_currency = get_account_currency(account)
							credit_amount = (
								flt(amount["base_amount"])
								if (amount["base_amount"] or account_currency != self.company_currency)
								else flt(amount["amount"])
							)

							self.add_gl_entry(
								gl_entries=gl_entries,
								account=account,
								cost_center=d.cost_center,
								debit=0.0,
								credit=credit_amount,
								remarks=remarks,
								against_account=warehouse_account_name,
								credit_in_account_currency=flt(amount["amount"]),
								account_currency=account_currency,
								project=d.project,
								item=d,
							)

					if d.rate_difference_with_purchase_invoice and stock_rbnb:
						account_currency = get_account_currency(stock_rbnb)
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=stock_rbnb,
							cost_center=d.cost_center,
							debit=0.0,
							credit=flt(d.rate_difference_with_purchase_invoice),
							remarks=frappe._("Adjustment based on Purchase Invoice rate"),
							against_account=warehouse_account_name,
							account_currency=account_currency,
							project=d.project,
							item=d,
						)

					# sub-contracting warehouse
					if flt(d.rm_supp_cost) and warehouse_account.get(self.supplier_warehouse):
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=supplier_warehouse_account,
							cost_center=d.cost_center,
							debit=0.0,
							credit=flt(d.rm_supp_cost),
							remarks=remarks,
							against_account=warehouse_account_name,
							account_currency=supplier_warehouse_account_currency,
							item=d,
						)

					# divisional loss adjustment
					valuation_amount_as_per_doc = (
						flt(outgoing_amount, d.precision("base_net_amount"))
						+ flt(d.landed_cost_voucher_amount)
						+ flt(d.rm_supp_cost)
						+ flt(d.item_tax_amount)
						+ flt(d.rate_difference_with_purchase_invoice)
					)

					divisional_loss = flt(
						valuation_amount_as_per_doc - flt(stock_value_diff), d.precision("base_net_amount")
					)

					if divisional_loss:
						if self.is_return or flt(d.item_tax_amount):
							loss_account = expenses_included_in_valuation
						else:
							loss_account = (
								self.get_company_default("default_expense_account", ignore_validation=True) or stock_rbnb
							)

						cost_center = d.cost_center or frappe.get_cached_value(
							"Company", self.company, "cost_center"
						)

						self.add_gl_entry(
							gl_entries=gl_entries,
							account=loss_account,
							cost_center=cost_center,
							debit=divisional_loss,
							credit=0.0,
							remarks=remarks,
							against_account=warehouse_account_name,
							account_currency=credit_currency,
							project=d.project,
							item=d,
						)

				elif (
					d.warehouse not in warehouse_with_no_account
					or d.rejected_warehouse not in warehouse_with_no_account
				):
					warehouse_with_no_account.append(d.warehouse)
			elif (
				d.item_code not in stock_items
				and not d.is_fixed_asset
				and flt(d.qty)
				and provisional_accounting_for_non_stock_items
				and d.get("provisional_expense_account")
			):
				self.add_provisional_gl_entry(
					d, gl_entries, self.posting_date, d.get("provisional_expense_account")
				)

		if warehouse_with_no_account:
			frappe.msgprint(
				frappe._("No accounting entries for the following warehouses")
				+ ": \n"
				+ "\n".join(warehouse_with_no_account)
			)


def get_item_account_wise_additional_cost(purchase_document, lc_from_pi=None):
	"""
	Function copied/modified from ERPNext's PurchaseReceipt class in purchase_receipt.py
	        to accommodate revised function signature and inline landed costs in a linked
	        Purchase Invoice
	New parameter lc_from_pi is None unless Enable Inline Landed Costing
	        feature is set and landed costs are included in a Purchase Invoice
	"""
	landed_cost_vouchers = frappe.get_all(
		"Landed Cost Purchase Receipt",
		fields=["parent"],
		filters={"receipt_document": purchase_document, "docstatus": 1},
	)

	if not landed_cost_vouchers and not lc_from_pi:  # CUSTOM CODE
		return

	item_account_wise_cost = {}

	for lcv in landed_cost_vouchers:
		landed_cost_voucher_doc = frappe.get_doc("Landed Cost Voucher", lcv.parent)

		# Use amount field for total item cost for manually cost distributed LCVs
		if landed_cost_voucher_doc.distribute_charges_based_on == "Distribute Manually":
			based_on_field = "amount"
		else:
			based_on_field = frappe.scrub(landed_cost_voucher_doc.distribute_charges_based_on)

		total_item_cost = 0

		for item in landed_cost_voucher_doc.items:
			total_item_cost += item.get(based_on_field)

		for item in landed_cost_voucher_doc.items:
			if item.receipt_document == purchase_document:
				for account in landed_cost_voucher_doc.taxes:
					item_account_wise_cost.setdefault((item.item_code, item.purchase_receipt_item), {})
					item_account_wise_cost[(item.item_code, item.purchase_receipt_item)].setdefault(
						account.expense_account, {"amount": 0.0, "base_amount": 0.0}
					)
					# TODO: review diff between if/else (new else block added from v13->v14)
					if total_item_cost > 0:
						item_account_wise_cost[(item.item_code, item.purchase_receipt_item)][
							account.expense_account
						]["amount"] += (
							account.amount * item.get(based_on_field) / total_item_cost
						)

						item_account_wise_cost[(item.item_code, item.purchase_receipt_item)][
							account.expense_account
						]["base_amount"] += (
							account.base_amount * item.get(based_on_field) / total_item_cost
						)
					else:
						item_account_wise_cost[(item.item_code, item.purchase_receipt_item)][
							account.expense_account
						]["amount"] += item.applicable_charges
						item_account_wise_cost[(item.item_code, item.purchase_receipt_item)][
							account.expense_account
						]["base_amount"] += item.applicable_charges

	# CUSTOM CODE START
	if lc_from_pi:
		item_account_wise_cost.update(lc_from_pi)
	# CUSTOM CODE END

	return item_account_wise_cost
