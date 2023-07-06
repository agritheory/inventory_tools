import json

import frappe
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice


class CustomPurchaseInvoice(PurchaseInvoice):
	def validate(self):
		# TODO: validate the 'to pay' qty col in subcontracting is not more than total qty col for each row
		return super().validate()

	def on_submit(self):
		# TODO: Save the paid-for qty for items in the stock entry detail field
		return super().on_submit()

	def on_cancel(self):
		# TODO: Revert the paid-for qty for items in the stock entry detail field
		return super().on_cancel()


@frappe.whitelist()
def get_stock_entries_by_work_order(work_orders):
	if isinstance(work_orders, str):
		work_orders = json.loads(work_orders)
	stock_entry = frappe.qb.DocType("Stock Entry")
	se_detail = frappe.qb.DocType("Stock Entry Detail")

	query = (
		frappe.qb.from_(stock_entry)
		.inner_join(se_detail)
		.on(stock_entry.name == se_detail.parent)
		.select(
			(stock_entry.name).as_("stock_entry"),
			stock_entry.work_order,
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
		.where(stock_entry.work_order.isin(work_orders))
		.where(se_detail.is_finished_item == 1)
	)

	return frappe.db.sql(query.get_sql(), {"work_orders": work_orders}, as_dict=1)

	## EQUIVALENT SQL QUERY
	# return frappe.db.sql(f"""
	# 	SELECT
	# 		`tabStock Entry`.name AS stock_entry,
	# 		`tabStock Entry`.work_order AS work_order,
	# 		`tabStock Entry Detail`.item_code AS item_code,
	# 		`tabStock Entry Detail`.item_name AS item_name,
	# 		`tabStock Entry Detail`.qty AS qty,
	# 		`tabStock Entry Detail`.transfer_qty AS transfer_qty,
	# 		`tabStock Entry Detail`.uom AS uom,
	# 		`tabStock Entry Detail`.stock_uom AS stock_uom,
	# 		`tabStock Entry Detail`.conversion_factor AS conversion_factor,
	# 		`tabStock Entry Detail`.valuation_rate AS valuation_rate,
	# 		`tabStock Entry Detail`.paid_qty AS paid_qty
	# 	FROM `tabStock Entry`, `tabStock Entry Detail`
	# 	WHERE
	# 		`tabStock Entry`.name = `tabStock Entry Detail`.parent
	# 		AND `tabStock Entry`.docstatus = 1
	# 		AND `tabStock Entry`.stock_entry_type = 'Manufacture'
	# 		AND `tabStock Entry`.work_order IN %(work_orders)s
	# 		AND `tabStock Entry Detail`.is_finished_item = 1
	# 	""",
	# 	{'work_orders': work_orders},
	# 	as_dict=1
	# )
