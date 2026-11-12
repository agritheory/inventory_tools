# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.manufacturing.doctype.bom.bom import BOM
from frappe.utils import flt


class InventoryToolsBOM(BOM):
	def get_routing(self):
		"""
		HASH: a6881039e6ae305726b2e9b88ac7ca3fd799bd2d
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/manufacturing/doctype/bom/bom.py
		METHOD: get_routing

		Adds the operation relation fields to the copied Routing fields.
		"""
		if self.routing:
			self.set("operations", [])
			fields = [
				"sequence_id",
				"operation",
				"workstation",
				"workstation_type",
				"description",
				"time_in_mins",
				"batch_size",
				"operating_cost",
				"idx",
				"hour_rate",
				"set_cost_based_on_bom_qty",
				"fixed_time",
				"predecessor_relation",
				"lag_mins",
			]

			for row in frappe.get_all(
				"BOM Operation",
				fields=fields,
				filters={"parenttype": "Routing", "parent": self.routing},
				order_by="sequence_id, idx",
			):
				child = self.append("operations", row)
				child.hour_rate = flt(row.hour_rate / self.conversion_rate, child.precision("hour_rate"))
