# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.manufacturing.doctype.bom.bom import BOM
from frappe.utils import flt, getdate, nowdate


class InventoryToolsBOM(BOM):
	@frappe.whitelist()
	def update_cost(
		self,
		update_parent=True,
		from_child_bom=False,
		update_hour_rate=True,
		save=True,
		as_of_date=None,
	):
		self._as_of_date = getdate(as_of_date) if as_of_date else getdate(nowdate())
		return super().update_cost(
			update_parent=update_parent,
			from_child_bom=from_child_bom,
			update_hour_rate=update_hour_rate,
			save=save,
		)

	def update_rate_and_time(self, row, update_hour_rate=False):
		as_of_date = getattr(self, "_as_of_date", getdate(nowdate()))

		if not row.hour_rate or update_hour_rate:
			hour_rate = self._get_workstation_hour_rate(row.workstation, as_of_date)
			if hour_rate is not None:
				row.hour_rate = (
					hour_rate / flt(self.conversion_rate) if self.conversion_rate and hour_rate else hour_rate
				)
			else:
				cached_rate = flt(frappe.get_cached_value("Workstation", row.workstation, "hour_rate"))
				if cached_rate:
					row.hour_rate = (
						cached_rate / flt(self.conversion_rate)
						if self.conversion_rate and cached_rate
						else cached_rate
					)

		if row.hour_rate and row.time_in_mins:
			row.base_hour_rate = flt(row.hour_rate) * flt(self.conversion_rate)
			row.operating_cost = flt(row.hour_rate) * flt(row.time_in_mins) / 60.0
			row.base_operating_cost = flt(row.operating_cost) * flt(self.conversion_rate)
			row.cost_per_unit = row.operating_cost / (row.batch_size or 1.0)
			row.base_cost_per_unit = row.base_operating_cost / (row.batch_size or 1.0)

		if update_hour_rate:
			row.db_update()

	def _get_workstation_hour_rate(self, workstation_name, as_of_date):
		"""Sum costs from workstation_operating_cost table that cover the given date."""
		rows = frappe.get_all(
			"Workstation Operating Cost",
			filters={"parent": workstation_name},
			fields=["from_date", "to_date", "qty"],
		)

		if not rows:
			return None

		net_hour_rate = 0.0
		has_match = False
		for row in rows:
			from_date = getdate(row.from_date) if row.from_date else None
			to_date = getdate(row.to_date) if row.to_date else None

			if from_date and from_date <= as_of_date:
				if to_date is None or as_of_date <= to_date:
					net_hour_rate += flt(row.qty)
					has_match = True

		return net_hour_rate if has_match else None
