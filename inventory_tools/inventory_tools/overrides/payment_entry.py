# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import (
	PaymentEntry,
	get_outstanding_reference_documents,
)
from frappe import ValidationError, _, throw
from frappe.utils import flt, get_link_to_form


class InventoryToolsPaymentEntry(PaymentEntry):
	def validate_allocated_amount(self):
		if self.payment_type == "Internal Transfer":
			return

		if self.party_type in ("Customer", "Supplier"):
			self.validate_allocated_amount_with_latest_data()
		else:
			fail_message = _(
				"{0} Row {1} / {2}: Allocated Amount of {3} cannot be greater than outstanding amount of {4}."
			)
			for d in self.get("references"):
				if (flt(d.allocated_amount)) > 0 and flt(d.allocated_amount) > flt(d.outstanding_amount):
					frappe.throw(
						fail_message.format(
							self.party_name,
							d.idx,
							get_link_to_form(d.reference_doctype, d.reference_name),
							d.allocated_amount,
							d.outstanding_amount,
						)
					)

				# Check for negative outstanding invoices as well
				if flt(d.allocated_amount) < 0 and flt(d.allocated_amount) < flt(d.outstanding_amount):
					frappe.throw(
						fail_message.format(
							self.party_name,
							d.idx,
							get_link_to_form(d.reference_doctype, d.reference_name),
							d.allocated_amount,
							d.outstanding_amount,
						)
					)

	def validate_allocated_amount_with_latest_data(self):
		if self.references:
			uniq_vouchers = {(x.reference_doctype, x.reference_name) for x in self.references}
			vouchers = [frappe._dict({"voucher_type": x[0], "voucher_no": x[1]}) for x in uniq_vouchers]
			latest_references = get_outstanding_reference_documents(
				{
					"posting_date": self.posting_date,
					"company": self.company,
					"party_type": self.party_type,
					"payment_type": self.payment_type,
					"party": self.party,
					"party_account": self.paid_from if self.payment_type == "Receive" else self.paid_to,
					"get_outstanding_invoices": True,
					"get_orders_to_be_billed": True,
					"vouchers": vouchers,
				}
			)

			# Group latest_references by (voucher_type, voucher_no)
			latest_lookup = {}
			for d in latest_references:
				d = frappe._dict(d)
				latest_lookup.setdefault((d.voucher_type, d.voucher_no), frappe._dict())[d.payment_term] = d

			for idx, d in enumerate(self.get("references"), start=1):
				latest = latest_lookup.get((d.reference_doctype, d.reference_name)) or frappe._dict()

				# If term based allocation is enabled, throw
				if (
					d.payment_term is None or d.payment_term == ""
				) and self.term_based_allocation_enabled_for_reference(
					d.reference_doctype, d.reference_name
				):
					frappe.throw(
						_(
							"{0} has Payment Term based allocation enabled. Select a Payment Term for Row #{1} in Payment References section"
						).format(frappe.bold(d.reference_name), frappe.bold(idx))
					)

				# if no payment template is used by invoice and has a custom term(no `payment_term`), then invoice outstanding will be in 'None' key
				latest = latest.get(d.payment_term) or latest.get(None)
				# The reference has already been fully paid
				if not latest:
					frappe.throw(
						_("{0} {1} has already been fully paid.").format(_(d.reference_doctype), d.reference_name)
					)
				# The reference has already been partly paid
				elif (
					latest.outstanding_amount < latest.invoice_amount
					and flt(d.outstanding_amount, d.precision("outstanding_amount"))
					!= flt(latest.outstanding_amount, d.precision("outstanding_amount"))
					and d.payment_term == ""
				):
					frappe.throw(
						_(
							"{0} {1} has already been partly paid. Please use the 'Get Outstanding Invoice' or the 'Get Outstanding Orders' button to get the latest outstanding amounts."
						).format(_(d.reference_doctype), d.reference_name)
					)

				fail_message = _(
					"<b>Row #{1}</b> {0} / {2}: Allocated Amount of {3} cannot be greater than outstanding amount of {4}."
				)

				if (
					d.payment_term
					and (
						(flt(d.allocated_amount)) > 0
						and latest.payment_term_outstanding
						and (flt(d.allocated_amount) > flt(latest.payment_term_outstanding))
					)
					and self.term_based_allocation_enabled_for_reference(d.reference_doctype, d.reference_name)
				):
					frappe.throw(
						_(
							"Row #{0}: Allocated amount:{1} is greater than outstanding amount:{2} for Payment Term {3}"
						).format(
							d.idx, d.allocated_amount, latest.payment_term_outstanding, d.payment_term
						)
					)

				if (flt(d.allocated_amount)) > 0 and flt(d.allocated_amount) > flt(latest.outstanding_amount):
					frappe.throw(
						fail_message.format(
							self.party_name,
							d.idx,
							get_link_to_form(d.reference_doctype, d.reference_name),
							d.allocated_amount,
							d.outstanding_amount,
						)
					)

				# Check for negative outstanding invoices as well
				if flt(d.allocated_amount) < 0 and flt(d.allocated_amount) < flt(latest.outstanding_amount):
					frappe.throw(
						fail_message.format(
							self.party_name,
							d.idx,
							get_link_to_form(d.reference_doctype, d.reference_name),
							d.allocated_amount,
							d.outstanding_amount,
						)
					)
