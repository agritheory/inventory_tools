# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.doctype.material_request.material_request import MaterialRequest
from erpnext.stock.get_item_details import get_price_list_rate_for
from frappe import _
from frappe.utils import cint, flt


class InventoryToolsMaterialRequest(MaterialRequest):
	def on_update(self):
		"""
		HASH: b4855399b07071fed04366a3bb2fb1e74fdf760e
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/stock/doctype/material_request/material_request.py
		METHOD: on_update
		"""
		# CUSTOM CODE START
		# is_new() is already False here during insert because db_insert clears __islocal
		if self.flags.in_insert:
			return
		# CUSTOM CODE END
		if not self.is_new() and self.buying_price_list and self.has_value_changed("buying_price_list"):
			self.update_item_rates()

	def update_item_rates(self):
		"""
		HASH: b4855399b07071fed04366a3bb2fb1e74fdf760e
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/stock/doctype/material_request/material_request.py
		METHOD: update_item_rates
		"""
		price_not_uom_dependent = frappe.get_value(
			"Price List", self.buying_price_list, "price_not_uom_dependent"
		)
		updated = False  # CUSTOM CODE
		for item in self.items:
			# CUSTOM CODE START
			if cint(frappe.get_cached_value("Item", item.item_code, "is_generic_item")):
				continue
			# CUSTOM CODE END
			rate = get_price_list_rate_for(
				frappe._dict(
					{
						"price_list": self.buying_price_list,
						"uom": item.uom,
						"transaction_date": self.transaction_date,
						"qty": item.qty,
						"stock_uom": item.stock_uom,
						"conversion_factor": item.conversion_factor,
						"price_list_uom_dependant": price_not_uom_dependent,
					}
				),
				item.item_code,
			)
			# CUSTOM CODE START
			if rate is not None and flt(rate) != flt(item.rate):
				item.db_set({"rate": rate, "amount": flt(rate * item.qty, item.precision("amount"))})
				updated = True

		if not updated:
			return
		# CUSTOM CODE END

		frappe.msgprint(
			_("Item rates have been updated based on the selected Buying Price List {0}").format(
				self.buying_price_list
			),
			alert=True,
		)
