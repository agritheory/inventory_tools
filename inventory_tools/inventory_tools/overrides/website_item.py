# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe

from webshop.webshop.doctype.website_item.website_item import WebsiteItem
from inventory_tools.inventory_tools.faceted_search_query import get_website_product_info
from webshop.webshop.shopping_cart.cart import get_party


class InventoryToolsWebsiteItem(WebsiteItem):
	def set_shopping_cart_data(self, context):
		its = frappe.get_last_doc("Inventory Tools Settings")
		if not its.show_on_website:
			super().set_shopping_cart_data(context)
		else:
			party = get_party()
			quotation = frappe.get_all(
				"Quotation",
				fields=["name"],
				filters={
					"party_name": party.name,
					"contact_email": frappe.session.user,
					"order_type": "Shopping Cart",
					"docstatus": 0,
				},
				order_by="modified desc",
				limit_page_length=1,
			)
			context.shopping_cart = get_website_product_info(
				self.item_code, skip_quotation_creation=not bool(quotation)
			)
			context.shopping_cart.cart_items = []
			if quotation:
				context.shopping_cart.cart_items = frappe.get_all(
					"Quotation Item", {"parent": quotation[0].name}, ["item_code"], pluck="item_code"
				)
