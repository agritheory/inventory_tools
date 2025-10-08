# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class WorkstationOperatingCost(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		consumable_cost: DF.Currency
		electricity_cost: DF.Currency
		from_date: DF.Date | None
		net_hour_rate: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rent_cost: DF.Currency
		to_date: DF.Date | None
		wages: DF.Currency
	# end: auto-generated types
