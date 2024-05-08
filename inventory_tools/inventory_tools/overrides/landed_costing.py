import frappe
from erpnext.stock.get_item_details import get_conversion_factor
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def update_valuation_rate(self, reset_outgoing_rate=True):
	"""
	Common code for InventoryToolsPurchaseReceipt and InventoryToolsPurchaseInvoice. This function
	overrides the BuyingController's (mutual parent to PR and PI) class function, called in
	`validate()`.

	item_tax_amount is the total allocated tax amount applied on item and stored for valuation. Tax
	amounts are only allocated when the tax.category attribute is either 'Valuation' or 'Valuation
	and Total'

	:param self: expects class instance of either a Purchase Receipt or Purchase Invoice document
	:param reset_outgoing_rate: bool
	:return: Nonetype
	"""
	stock_and_asset_items = []
	stock_and_asset_items = self.get_stock_items() + self.get_asset_items()

	stock_and_asset_items_qty, stock_and_asset_items_amount = 0, 0
	last_item_idx = 1
	for d in self.get("items"):
		if d.item_code and d.item_code in stock_and_asset_items:
			stock_and_asset_items_qty += flt(d.qty)
			stock_and_asset_items_amount += flt(d.base_net_amount)
			last_item_idx = d.idx

	# CUSTOM CODE BEGIN
	based_on = self.get("distribute_charges_based_on")
	total_valuation_amount = sum(
		flt(d.base_tax_amount_after_discount_amount)
		for d in self.get("taxes")
		if d.category in ["Valuation", "Valuation and Total"]
	)
	div_by_zero_flag = (based_on == "Qty" and not stock_and_asset_items_qty) or (
		based_on == "Amount" and not stock_and_asset_items_amount
	)

	valuation_amount_adjustment = total_valuation_amount
	for i, item in enumerate(self.get("items")):
		if item.item_code and item.qty and item.item_code in stock_and_asset_items:
			if div_by_zero_flag:
				field = "Accepted Quantity" if based_on == "Qty" else "Amount"
				frappe.throw(
					_(f"{field} values can't total zero when distributing charges based on {based_on}")
				)
			if based_on == "Don't Distribute":
				item.item_tax_amount = 0.0
			else:
				item_proportion = (
					flt(item.qty) / stock_and_asset_items_qty
					if based_on == "Qty"
					else flt(item.base_net_amount) / stock_and_asset_items_amount
				)

				if i == (last_item_idx - 1):
					item.item_tax_amount = flt(
						valuation_amount_adjustment, self.precision("item_tax_amount", item)
					)
				else:
					item.item_tax_amount = flt(
						item_proportion * total_valuation_amount, self.precision("item_tax_amount", item)
					)
					valuation_amount_adjustment -= item.item_tax_amount

			self.round_floats_in(item)
			if flt(item.conversion_factor) == 0.0:
				item.conversion_factor = (
					get_conversion_factor(item.item_code, item.uom).get("conversion_factor") or 1.0
				)

			qty_in_stock_uom = flt(item.qty * item.conversion_factor)
			if self.get("is_old_subcontracting_flow"):
				item.rm_supp_cost = self.get_supplied_items_cost(
					item.name, reset_outgoing_rate
				)  # in subcontracting_controller.py
				item.valuation_rate = (
					item.base_net_amount
					+ item.item_tax_amount
					+ item.rm_supp_cost
					+ flt(item.landed_cost_voucher_amount)
				) / qty_in_stock_uom
			# TODO: add branch to handle subcontracting workflow to update valuation depending on settings [include raw materials value / get from stock entry?]
			# CUSTOM CODE END
			else:
				item.valuation_rate = (
					item.base_net_amount
					+ item.item_tax_amount
					+ flt(item.landed_cost_voucher_amount)
					+ flt(item.get("rate_difference_with_purchase_invoice"))
				) / qty_in_stock_uom
		else:
			item.valuation_rate = 0.0
