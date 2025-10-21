# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate, getdate


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
	costs = sorted(doc.workstation_operating_cost, key=lambda x: x.from_date)

	for i, row in enumerate(costs):
		# Automatically set to_date if not present
		if not row.to_date:
			if i + 1 < len(costs):
				row.to_date = costs[i + 1].from_date
			else:
				row.to_date = None  # open-ended if last row

	# Reorder by descending from_date
	doc.workstation_operating_cost.sort(key=lambda x: x.from_date or "1970-01-01", reverse=True)

	# Check overlap
	for i in range(len(costs) - 1):
		if costs[i].to_date and costs[i].to_date > costs[i + 1].from_date:
			frappe.throw(
				_("Cost periods cannot overlap. Row {0} overlaps with Row {1}").format(i + 1, i + 2)
			)

	# Populate latest rates into legacy fields
	if costs:
		latest = costs[0]
		doc.hour_rate_electricity = latest.electricity_cost
		doc.hour_rate_consumable = latest.consumable_cost
		doc.hour_rate_rent = latest.rent_cost
		doc.hour_rate_labour = latest.wages
		# doc.net_hour_rate = latest.net_hour_rate


def validate_dates(doc, method):
	for row in doc.workstation_operating_cost:
		if row.from_date and row.to_date:
			if row.from_date > row.to_date:
				frappe.throw(_("From Date cannot be after To Date in Workstation Operating Cost."))

			if row.to_date < row.from_date:
				frappe.throw(_("To Date cannot be before From Date in Workstation Operating Cost."))


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
				row_cost = (
					flt(matched_row.electricity_cost)
					+ flt(matched_row.consumable_cost)
					+ flt(matched_row.rent_cost)
				)
				if flt(op.completed_qty):
					operating_cost_per_unit += row_cost / flt(op.completed_qty)
				elif work_order.qty:
					operating_cost_per_unit += row_cost / flt(work_order.qty)

	return operating_cost_per_unit
