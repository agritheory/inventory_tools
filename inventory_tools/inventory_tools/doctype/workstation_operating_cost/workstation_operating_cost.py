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

		consumable_cost: DF.Currency
		electricity_cost: DF.Currency
		from_date: DF.Date | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rent_cost: DF.Currency
		to_date: DF.Date | None
		wages: DF.Currency
	# end: auto-generated types


def validate_workstation_costs(doc, method):
	for idx, r in enumerate(doc.workstation_operating_cost, start=1):
		if not r.from_date:
			frappe.throw(_("Row {0}: 'From Date' is required.").format(idx))

	costs = sorted(doc.workstation_operating_cost, key=lambda x: getdate(x.from_date))

	for i, row in enumerate(costs):
		if not row.to_date:
			if i + 1 < len(costs):
				next_from = getdate(costs[i + 1].from_date)
				row.to_date = add_days(next_from, -1)
			else:
				row.to_date = None

	for i in range(len(costs) - 1):
		cur_to = costs[i].to_date
		next_from = costs[i + 1].from_date

		if cur_to and next_from:
			if getdate(cur_to) >= getdate(next_from):
				frappe.throw(
					_("Cost periods cannot overlap. Row {0} overlaps with Row {1}").format(i + 1, i + 2)
				)

	doc.workstation_operating_cost.sort(key=lambda x: getdate(x.from_date), reverse=True)

	for i, row in enumerate(doc.workstation_operating_cost, start=1):
		row.idx = i

	if doc.workstation_operating_cost:
		latest = doc.workstation_operating_cost[0]
		doc.hour_rate_electricity = latest.electricity_cost
		doc.hour_rate_consumable = latest.consumable_cost
		doc.hour_rate_rent = latest.rent_cost
		doc.hour_rate_labour = latest.wages


def validate_dates(doc, method):
	for idx, row in enumerate(doc.workstation_operating_cost, start=1):
		if row.from_date and row.to_date:
			from_date = getdate(row.from_date)
			to_date = getdate(row.to_date)

			if from_date > to_date:
				frappe.throw(
					_("Row {0}: From Date cannot be after To Date in Workstation Operating Cost.").format(idx)
				)


def get_operating_cost_per_unit_with_date_range(work_order=None, bom_no=None, posting_date=None):
	"""Extended version that adds date-range-based cost lookup."""
	operating_cost_per_unit = 0
	posting_date = getdate(posting_date or nowdate())

	if work_order and hasattr(work_order, "operations"):
		for op in work_order.get("operations"):
			if not op.workstation:
				continue

			ws = frappe.get_doc("Workstation", op.workstation)
			matched_row = None

			for row in ws.workstation_operating_cost:
				from_date = getdate(row.from_date) if row.from_date else None
				to_date = getdate(row.to_date) if row.to_date else None

				if from_date and to_date:
					if from_date <= posting_date <= to_date:
						matched_row = row
						break
				elif from_date and not to_date:
					if from_date <= posting_date:
						matched_row = row
						break

			if matched_row:
				# Hourly cost rate
				hourly_cost = (
					flt(matched_row.electricity_cost)
					+ flt(matched_row.consumable_cost)
					+ flt(matched_row.rent_cost)
				)

				# ✅ FIX: Calculate total operation cost (hourly_cost × hours)
				hours = flt(op.time_in_mins) / 60.0
				total_operation_cost = hourly_cost * hours

				# ✅ FIX: Divide by work order quantity to get per-unit cost
				if flt(op.completed_qty):
					operating_cost_per_unit += total_operation_cost / flt(op.completed_qty)
				elif work_order.qty:
					operating_cost_per_unit += total_operation_cost / flt(work_order.qty)

	return operating_cost_per_unit
