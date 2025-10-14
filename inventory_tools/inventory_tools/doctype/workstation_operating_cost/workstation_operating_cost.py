# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def validate_workstation_costs(doc, method):
	costs = sorted(doc.workstation_operating_costs, key=lambda x: x.from_date)

	for i, row in enumerate(costs):
		# Automatically set to_date if not present
		if not row.to_date:
			if i + 1 < len(costs):
				row.to_date = costs[i + 1].from_date
			else:
				row.to_date = None  # open-ended if last row

	# Reorder by descending from_date
	doc.workstation_operating_costs.sort(key=lambda x: x.from_date or "1970-01-01", reverse=True)

	# Check overlap
	for i in range(len(costs) - 1):
		if costs[i].to_date and costs[i].to_date > costs[i + 1].from_date:
			frappe.throw(
				_("Cost periods cannot overlap. Row {0} overlaps with Row {1}").format(i + 1, i + 2)
			)

	# Populate latest rates into legacy fields
	if costs:
		latest = costs[0]
		doc.electricity_cost = latest.electricity_cost
		doc.consumable_cost = latest.consumable_cost
		doc.rent_cost = latest.rent_cost
		doc.wages = latest.wages
		doc.net_hour_rate = latest.net_hour_rate


@frappe.whitelist()
def get_cost(workstation, date=None):
	if not date:
		date = frappe.utils.nowdate()
	costs = frappe.get_all(
		"Workstation Operating Cost",
		filters={"parent": workstation, "from_date": ["<=", date], "to_date": [">=", date]},
		order_by="from_date desc",
		limit_page_length=1,
		fields=["electricity_cost", "consumable_cost", "rent_cost", "wages", "net_hour_rate"],
	)
	return costs[0] if costs else {}
