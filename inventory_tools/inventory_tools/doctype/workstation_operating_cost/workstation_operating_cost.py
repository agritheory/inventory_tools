# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate, getdate, add_days


class WorkstationOperatingCost(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link
		from_date: DF.Date
		item_code: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		qty: DF.Float
		to_date: DF.Date | None
	# end: auto-generated types


def validate_workstation_costs(doc, method):
	# Validate required fields
	for idx, r in enumerate(doc.workstation_operating_cost, start=1):
		if not r.from_date:
			frappe.throw(_("Row {0}: 'From Date' is required.").format(idx))
	# Sort by account, then from_date and auto-fill to_dates
	costs = sorted(doc.workstation_operating_cost, key=lambda x: (x.account, getdate(x.from_date)))

	for i, row in enumerate(costs):
		if not row.to_date:
			if i + 1 < len(costs) and row.account == costs[i + 1].account:
				next_from = getdate(costs[i + 1].from_date)
				row.to_date = add_days(next_from, -1)
			else:
				row.to_date = None

	# Group sorted rows by account
	account_costs = {}
	for row in costs:
		if row.account not in account_costs:
			account_costs[row.account] = []
		account_costs[row.account].append((row.idx, row))

	# Check for overlapping periods within each account
	for account, account_rows in account_costs.items():
		for i in range(len(account_rows) - 1):
			cur_idx, cur_row = account_rows[i]
			next_idx, next_row = account_rows[i + 1]

			cur_to = cur_row.to_date
			next_from = next_row.from_date

			if cur_to and next_from:
				if getdate(cur_to) >= getdate(next_from):
					frappe.throw(
						_("Account '{0}': Cost periods cannot overlap. Row {1} overlaps with Row {2}").format(
							account, cur_idx, next_idx
						)
					)

	doc.workstation_operating_cost.sort(
		key=lambda x: (x.account or "", getdate(x.from_date)), reverse=True
	)

	for i, row in enumerate(doc.workstation_operating_cost, start=1):
		row.idx = i


def validate_dates(doc, method):
	for idx, row in enumerate(doc.workstation_operating_cost, start=1):
		if row.from_date and row.to_date:
			from_date = getdate(row.from_date)
			to_date = getdate(row.to_date)

			if from_date > to_date:
				frappe.throw(
					_("Row {0}: From Date cannot be after To Date in Workstation Operating Cost.").format(idx)
				)


def get_operating_costs_by_operation(
	work_order=None, bom_no=None, posting_date=None
) -> list[frappe._dict]:
	"""Returns operating costs per operation and account for the given date range."""
	posting_date = getdate(posting_date or nowdate())

	if not work_order or not hasattr(work_order, "operations"):
		return []

	operating_costs = []

	for op in work_order.get("operations"):
		if not op.workstation:
			continue

		ws = frappe.get_doc("Workstation", op.workstation)
		hours = flt(op.time_in_mins) / 60.0

		if ws.workstation_operating_cost:
			for row in ws.workstation_operating_cost:
				from_date = getdate(row.from_date) if row.from_date else None
				to_date = getdate(row.to_date) if row.to_date else None

				date_matches = False
				if from_date and to_date:
					if from_date <= posting_date <= to_date:
						date_matches = True
				elif from_date and not to_date:
					if from_date <= posting_date:
						date_matches = True

				if date_matches and row.account:
					total_cost = flt(row.qty) * hours

					qty = flt(work_order.qty)
					if qty:
						cost_per_unit = flt(total_cost / qty, 2)

						operation_name = op.operation or ws.workstation_name or ws.name
						account_short = row.account.split(" - ")[0] if " - " in row.account else row.account

						description_parts = [
							operation_name,
							ws.name,
							f"{hours:.2f} hrs @ ${flt(row.qty):.2f}/hr",
							f"${cost_per_unit:.2f}/unit",
							account_short,
						]

						if row.item_code:
							description_parts.append(f"Item: {row.item_code}")

						description = " | ".join(description_parts)

						operating_costs.append(
							frappe._dict(
								{"account": row.account, "cost_per_unit": cost_per_unit, "description": description}
							)
						)
		else:
			account = frappe.db.get_value("Company", ws.company, "expenses_included_in_valuation")
			cost_per_unit = flt((ws.hour_rate * hours) / flt(work_order.qty), 2)
			operating_costs.append(
				frappe._dict(
					{
						"account": account,
						"cost_per_unit": cost_per_unit,
						"description": f"Net Cost from {ws.name}",
					}
				)
			)

	return operating_costs


@frappe.whitelist()
def fetch_default_expense_account(company, item_code):
	if item_code:
		return frappe.db.get_value(
			"Item Default", {"parent": item_code, "company": company}, ["expense_account"]
		)
