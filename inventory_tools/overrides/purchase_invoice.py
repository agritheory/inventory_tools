import datetime
import json

import frappe
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from frappe import _


class CustomPurchaseInvoice(PurchaseInvoice):
	def validate(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		if settings and settings.enable_work_order_subcontracting:
			for subc in self.get("subcontracting"):
				if subc.to_pay_qty > (subc.qty - subc.paid_qty):
					frappe.throw(
						_(
							f"The To Pay Qty in Subcontracting Detail row {subc.idx} cannot be more than Total Qty less the already Paid Qty."
						)
					)

		return super().validate()

	def on_submit(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		if settings and settings.enable_work_order_subcontracting:
			for ste in self.get("subcontracting"):
				frappe.db.set_value(
					"Stock Entry Detail", ste.se_detail_name, "paid_qty", ste.paid_qty + ste.to_pay_qty
				)

		return super().on_submit()

	def on_cancel(self):
		settings = frappe.get_doc("Inventory Tools Settings", {"company": self.company})
		if settings and settings.enable_work_order_subcontracting:
			for ste in self.get("subcontracting"):
				cur_paid = frappe.db.get_value("Stock Entry Detail", ste.se_detail_name, "paid_qty")
				frappe.db.set_value(
					"Stock Entry Detail", ste.se_detail_name, "paid_qty", cur_paid - ste.to_pay_qty
				)

		return super().on_cancel()


@frappe.whitelist()
def get_stock_entries(purchase_orders, from_date=None, to_date=None):
	# # Commented code is useful if having PO and attaching WOs to them is enforced
	# if isinstance(purchase_orders, str):
	# 	purchase_orders = json.loads(purchase_orders)

	if not from_date:
		from_date = datetime.date(1900, 1, 1)

	if not to_date:
		to_date = datetime.date(2100, 12, 31)

	# work_orders, fg_items = [], set()
	# for po in purchase_orders:
	# 	work_orders.extend(
	# 		frappe.get_all(
	# 			"Purchase Order Subcontracting Detail",
	# 			fields="work_order",
	# 			filters={"parent": po},
	# 			pluck="work_order"
	# 		)
	# 	)
	# 	for item in frappe.get_doc("Purchase Order", po).get("items"):
	# 		fg_items.add(item.get("fg_item"))

	stock_entry = frappe.qb.DocType("Stock Entry")
	se_detail = frappe.qb.DocType("Stock Entry Detail")
	po_sub = frappe.qb.DocType("Purchase Order Subcontracting Detail")
	item = frappe.qb.DocType("Item")

	query = (
		frappe.qb.from_(stock_entry)
		.inner_join(se_detail)
		.on(stock_entry.name == se_detail.parent)
		.left_join(po_sub)
		.on(stock_entry.work_order == po_sub.work_order)
		.left_join(item)
		.on(se_detail.item_code == item.item_code)
		.select(
			stock_entry.work_order,
			(stock_entry.name).as_("stock_entry"),
			(se_detail.name).as_("se_detail_name"),
			(po_sub.parent).as_("purchase_order"),
			se_detail.item_code,
			se_detail.item_name,
			se_detail.qty,
			se_detail.transfer_qty,
			se_detail.uom,
			se_detail.stock_uom,
			se_detail.conversion_factor,
			se_detail.valuation_rate,
			se_detail.paid_qty,
		)
		.where(stock_entry.docstatus == 1)
		.where(stock_entry.stock_entry_type == "Manufacture")
		.where(stock_entry.posting_date >= from_date)
		.where(stock_entry.posting_date <= to_date)
		# .where(stock_entry.work_order.isin(work_orders))
		# .where(se_detail.item_code.isin(fg_items))
		.where(se_detail.is_finished_item == 1)
		.where(se_detail.paid_qty < se_detail.qty)
		.where(item.is_sub_contracted_item == 1)
	)

	return frappe.db.sql(
		query.get_sql(),
		{
			"from_date": from_date,
			"to_date": to_date,
			# "work_orders": work_orders,
			# "fg_items": fg_items,
		},
		as_dict=1,
	)
