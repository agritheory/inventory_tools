# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.e_commerce.shopping_cart.cart import update_cart


def get_context(context):
	pass


@frappe.whitelist()
def create_quotation(bulk_paste: str):
	"""
	This function is for bulk orders:

	:param bulk_paste: string that contains item(s) and quantity(ies)
	"""

	if bulk_paste:
		bulk_paste.strip()
		for line_item in bulk_paste.split("\n"):
			if not line_item:
				continue
			item_code, qty = line_item.split("\t")
			frappe.enqueue(update_cart, item_code=item_code, qty=qty)
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = "/cart"
