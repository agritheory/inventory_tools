# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import json

import frappe
from erpnext.accounts.doctype.pricing_rule.pricing_rule import get_pricing_rule_for_item
from erpnext.stock.get_item_details import get_conversion_factor
from webshop.webshop.api import *
from webshop.webshop.doctype.webshop_settings.webshop_settings import (
	get_shopping_cart_settings,
	show_quantity_in_website,
)
from webshop.webshop.doctype.override_doctype.item_group import get_item_for_list_in_html
from webshop.webshop.doctype.item_review.item_review import get_customer
from webshop.webshop.product_data_engine.query import ProductQuery
from webshop.webshop.shopping_cart.cart import _get_cart_quotation, _set_price_list, get_party
from webshop.webshop.utils.product import (
	get_non_stock_item_status,
	adjust_qty_for_expired_items,
)
from frappe.utils.data import cint, flt, getdate, fmt_money

from inventory_tools.inventory_tools.doctype.specification.specification import (
	convert_to_epoch,
)

SORT_ORDER_LOOKUP = {
	"Title A-Z": "item_name ASC, ranking DESC",
	"Title Z-A": "item_name DESC, ranking DESC",
	"Item Code A-Z": "item_code ASC, ranking DESC",
	"Item Code Z-A": "item_code DESC, ranking DESC",
}


class FacetedSearchQuery(ProductQuery):
	def query(
		self,
		attributes=None,
		fields=None,
		search_term=None,
		start=0,
		item_group=None,
		sort_order="",
	):
		# track if discounts included in field filters
		self.filter_with_discount = bool(fields.get("discount"))
		result, discount_list, website_item_groups, cart_items, count = [], [], [], [], 0

		if fields:
			self.build_fields_filters(fields)
		if item_group:
			self.build_item_group_filters(item_group)
		if search_term:
			self.build_search_filters(search_term)
		if self.settings.hide_variants:
			self.filters.append(["variant_of", "is", "not set"])

		sort_order = SORT_ORDER_LOOKUP.get(sort_order) if sort_order else "item_name ASC"

		# query results
		if attributes:
			result, count = self.query_items_with_attributes(attributes, start, sort_order=sort_order)
		else:
			result, count = self.query_items(start=start, sort_order=sort_order)

		# sort combined results by ranking
		result = sorted(result, key=lambda x: x.get("ranking"), reverse=True)

		if self.settings.enabled:
			cart_items = self.get_cart_items()

		result, discount_list = self.add_display_details(result, discount_list, cart_items)

		discounts = []
		if discount_list:
			discounts = [min(discount_list), max(discount_list)]

		result = self.filter_results_by_discount(fields, result)

		return {"items": result, "items_count": count, "discounts": discounts}

	def query_items(self, start=0, sort_order=""):
		"""Build a query to fetch Website Items based on field filters."""
		# MySQL does not support offset without limit,
		# frappe does not accept two parameters for limit
		# https://dev.mysql.com/doc/refman/8.0/en/select.html#id4651989
		count_items = frappe.db.get_all(
			"Website Item",
			filters=self.filters,
			or_filters=self.or_filters,
			limit_page_length=184467440737095516,
			limit_start=start,  # get all items from this offset for total count ahead
			order_by=sort_order,
			# debug=True
		)
		count = len(count_items)

		# If discounts included, return all rows.
		# Slice after filtering rows with discount (See `filter_results_by_discount`).
		# Slicing before hand will miss discounted items on the 3rd or 4th page.
		# Discounts are fetched on computing Pricing Rules so we cannot query them directly.
		page_length = 184467440737095516 if self.filter_with_discount else self.page_length

		items = frappe.db.get_all(
			"Website Item",
			fields=self.fields,
			filters=self.filters,
			or_filters=self.or_filters,
			limit_page_length=page_length,
			limit_start=start,
			order_by=sort_order,
			# debug=True
		)

		return items, count

	def query_items_with_attributes(self, attributes, start=0, sort_order=""):
		item_codes = get_specification_items(attributes)

		if item_codes:
			item_codes = list(set.intersection(*item_codes))
			self.filters.append(["item_code", "in", item_codes])

		return self.query_items(start=start, sort_order=sort_order)


@frappe.whitelist()
def get_specification_items(attributes, start=0, sort_order=""):
	attributes = json.loads(attributes) if isinstance(attributes, str) else attributes
	item_codes = []

	attributes_in_use = {k: v for (k, v) in attributes.items() if v}
	for attribute, spec_and_values in attributes_in_use.items():
		spec = spec_and_values.get("attribute_id")
		values = spec_and_values.get("values")
		if not values:
			continue
		if not isinstance(values, list):
			values = [values]
		filters = None

		date_or_numeric = frappe.get_value(
			"Specification Attribute", spec, ["numeric_values", "date_values"]
		)
		if date_or_numeric[0] == 1:
			values[0], values[-1] = (
				flt(values[0]) if values[0] else None,
				flt(values[-1]) if values[-1] else None,
			)
			if values[0] and values[-1] and values[0] > values[-1]:
				values[0], values[-1] = values[-1], values[0]
			filters = [
				["attribute", "=", attribute],
			]
			if values[0]:
				filters.append(
					["value", ">=", flt(values[0])],
				)
			if values[-1]:
				filters.append(
					["value", "<=", flt(values[-1])],
				)

		elif date_or_numeric[1] == 1:
			filters = [
				["attribute", "=", attribute],
				[
					"value",
					">=",
					convert_to_epoch(getdate(values[0])) if values[0] else convert_to_epoch(getdate("1900-1-1")),
				],
				[
					"value",
					"<=",
					convert_to_epoch(getdate(values[-1]))
					if values[-1]
					else convert_to_epoch(getdate("2100-12-31")),
				],
			]
		else:
			filters = {
				"attribute": attribute,
				"value": ["in", values],
			}
		item_code_list = frappe.get_all(
			"Specification Value",
			fields=["reference_name"],
			filters=filters,  # debug=True
		)
		item_codes.append({x.reference_name for x in item_code_list})

	if item_codes:
		return list(item_codes)

	def add_display_details(self, result, discount_list, cart_items):
		"""Add price and availability details in result."""
		for item in result:
			product_info = get_product_info_for_website(item.item_code, skip_quotation_creation=True).get(
				"product_info"
			)

			if product_info and product_info["price"]:
				# update/mutate item and discount_list objects
				self.get_price_discount_info(item, product_info["price"], discount_list)

			if self.settings.show_stock_availability:
				self.get_stock_availability(item)

			item.in_cart = item.item_code in cart_items

			item.wished = False
			if frappe.db.exists(
				"Wishlist Item", {"item_code": item.item_code, "parent": frappe.session.user}
			):
				item.wished = True

		return result, discount_list


def get_product_info_for_website(item_code, skip_quotation_creation=False):
	cart_settings = get_shopping_cart_settings()
	if not cart_settings.enabled:
		# return settings even if cart is disabled
		return frappe._dict({"product_info": {}, "cart_settings": cart_settings})

	cart_quotation = frappe._dict()
	if not skip_quotation_creation:
		cart_quotation = _get_cart_quotation()

	selling_price_list = (
		cart_quotation.get("selling_price_list")
		if cart_quotation
		else _set_price_list(cart_settings, None)
	)

	customer = get_customer(silent=True)
	if customer:
		customer_group, customer_warehouse = frappe.db.get_value(
			"Customer", customer, ["customer_group", "up_default_warehouse"]
		)
		if not customer_warehouse:
			customer_warehouse = "Slauson Facility - UPIL"
		customer_uoms = frappe.get_all(
			"Item Customer Detail",
			{"parent": item_code},
			"uom",
			or_filters={"customer_name": customer, "customer_group": customer_group},
			pluck="uom",
		)
		uom = customer_uoms[0] if customer_uoms else None

	price = {}
	if cart_settings.show_price:
		is_guest = frappe.session.user == "Guest"
		# Show Price if logged in.
		# If not logged in, check if price is hidden for guest.
		if not is_guest or not cart_settings.hide_price_for_guest:
			price = get_product_price(
				item_code,
				selling_price_list,
				cart_settings.default_customer_group,
				cart_settings.company,
				uom=uom,
			)

	stock_status = None

	if cart_settings.show_stock_availability:
		on_backorder = frappe.get_cached_value("Website Item", {"item_code": item_code}, "on_backorder")
		if on_backorder:
			stock_status = frappe._dict({"on_backorder": True})
		else:
			stock_status = get_web_item_qty_in_stock(item_code, "website_warehouse", customer_warehouse)

	other_uoms = frappe.get_all("UOM Conversion Detail", ["uom"], {"parent": item_code}, pluck="uom")
	if customer_uoms:
		other_uoms = [o for o in other_uoms if o in customer_uoms]
	if not uom:
		uom = frappe.db.get_value("Item", item_code, "stock_uom")
	sales_uom = frappe.db.get_value("Item", item_code, "sales_uom")

	product_info = {
		"price": price,
		"qty": 0,
		"uom": uom,
		"sales_uom": sales_uom or uom,
		"other_uoms": other_uoms,
	}

	if stock_status:
		if stock_status.on_backorder:
			product_info["on_backorder"] = True
		else:
			product_info["stock_qty"] = stock_status.stock_qty
			product_info["in_stock"] = (
				stock_status.in_stock
				if stock_status.is_stock_item
				else get_non_stock_item_status(item_code, "website_warehouse")
			)
			product_info["show_stock_qty"] = show_quantity_in_website()

	if product_info["price"]:
		if frappe.session.user != "Guest":
			item = cart_quotation.get({"item_code": item_code}) if cart_quotation else None
			if item:
				product_info["qty"] = int(item[0].qty)

	return frappe._dict({"product_info": product_info, "cart_settings": cart_settings})


def set_product_info_for_website(item):
	"""set product price uom for website"""
	product_info = get_product_info_for_website(item.item_code, skip_quotation_creation=True).get(
		"product_info"
	)

	if product_info:
		item.update(product_info)
		item["stock_uom"] = product_info.get("uom")
		item["sales_uom"] = product_info.get("sales_uom")
		if product_info.get("price"):
			item["price_stock_uom"] = product_info.get("price").get("formatted_price")
			item["price_sales_uom"] = product_info.get("price").get("formatted_price_sales_uom")
		else:
			item["price_stock_uom"] = ""
			item["price_sales_uom"] = ""


@frappe.whitelist(allow_guest=True)
def get_product_list(search=None, start=0, limit=12):
	data = get_product_data(search, start, limit)

	for item in data:
		set_product_info_for_website(item)

	return [get_item_for_list_in_html(r) for r in data]


def get_product_price(item_code, price_list, customer_group, company, qty=1, uom=None):
	template_item_code = frappe.db.get_value("Item", item_code, "variant_of")

	if price_list:
		price = frappe.get_all(
			"Item Price",
			fields=["price_list_rate", "currency"],
			filters={"price_list": price_list, "item_code": item_code},
		)

		if template_item_code and not price:
			price = frappe.get_all(
				"Item Price",
				fields=["price_list_rate", "currency"],
				filters={"price_list": price_list, "item_code": template_item_code},
			)

		if price:
			party = get_party()
			stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
			customer_group = frappe.db.get_value("Customer", party.name, "customer_group")
			uom = frappe.get_all(
				"Item Customer Detail",
				{"parent": item_code},
				"uom",
				or_filters={"customer_name": party.name, "customer_group": customer_group},
			)
			if uom:
				uom = uom[0].get("uom")
			else:
				sales_uom, stock_uom = frappe.db.get_value("Item", item_code, ["sales_uom", "stock_uom"])
				uom = sales_uom if sales_uom else stock_uom

			conversion_factor = get_conversion_factor(item_code, uom).get("conversion_factor", 1)
			pricing_rule_dict = frappe._dict(
				{
					"item_code": item_code,
					"qty": qty,
					"uom": uom,
					"transaction_type": "selling",
					"price_list": price_list,
					"customer_group": customer_group,
					"company": company,
					"conversion_rate": conversion_factor,
					"for_shopping_cart": True,
					"currency": frappe.db.get_value("Price List", price_list, "currency"),
				}
			)

			if party and party.doctype == "Customer":
				pricing_rule_dict.update({"customer": party.name})

			pricing_rule = get_pricing_rule_for_item(pricing_rule_dict)
			price_obj = price[0]

			if pricing_rule:
				# price without any rules applied
				mrp = price_obj.price_list_rate or 0

				if pricing_rule.pricing_rule_for == "Discount Percentage":
					price_obj.discount_percent = pricing_rule.discount_percentage
					price_obj.formatted_discount_percent = str(flt(pricing_rule.discount_percentage, 0)) + "%"
					price_obj.price_list_rate = flt(
						price_obj.price_list_rate * (1.0 - (flt(pricing_rule.discount_percentage) / 100.0))
					)

				if pricing_rule.pricing_rule_for == "Rate":
					rate_discount = flt(mrp) - flt(pricing_rule.price_list_rate)
					if rate_discount > 0:
						price_obj.formatted_discount_rate = fmt_money(rate_discount, currency=price_obj["currency"])
					price_obj.price_list_rate = pricing_rule.price_list_rate or 0

			if price_obj:
				price_obj["formatted_price"] = fmt_money(
					price_obj["price_list_rate"], currency=price_obj["currency"]
				)
				if mrp != price_obj["price_list_rate"]:
					price_obj["formatted_mrp"] = fmt_money(mrp, currency=price_obj["currency"])

				price_obj["currency_symbol"] = (
					not cint(frappe.db.get_default("hide_currency_symbol"))
					and (
						frappe.db.get_value("Currency", price_obj.currency, "symbol", cache=True)
						or price_obj.currency
					)
					or ""
				)

				uom_conversion_factor = get_conversion_factor(item_code, uom)
				uom_conversion_factor = uom_conversion_factor.get("conversion_factor") or 1
				price_obj["formatted_price_sales_uom"] = fmt_money(
					price_obj["price_list_rate"] * uom_conversion_factor,
					currency=price_obj["currency"],
				)
				if uom_conversion_factor != 1:
					price_obj["formatted_price"] = price_obj["formatted_price_sales_uom"]

				if not price_obj["price_list_rate"]:
					price_obj["price_list_rate"] = price_obj["price_list_rate"] * uom_conversion_factor

				if not price_obj["currency"]:
					price_obj["currency"] = ""

				if not price_obj["formatted_price"]:
					price_obj["formatted_price"], price_obj["formatted_mrp"] = "", ""

			return price_obj


def get_web_item_qty_in_stock(item_code, item_warehouse_field, warehouse=None):
	in_stock, stock_qty = 0, ""
	template_item_code, is_stock_item = frappe.db.get_value(
		"Item", item_code, ["variant_of", "is_stock_item"]
	)

	if not warehouse:
		warehouse = frappe.db.get_value("Website Item", {"item_code": item_code}, item_warehouse_field)

	if not warehouse and template_item_code and template_item_code != item_code:
		warehouse = frappe.db.get_value(
			"Website Item", {"item_code": template_item_code}, item_warehouse_field
		)

	if warehouse:
		lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])
		from frappe.query_builder import functions as fn

		bin = frappe.qb.DocType("Bin")
		item = frappe.qb.DocType("Item")
		warehouse = frappe.qb.DocType("Warehouse")

		stock_qty = (
			frappe.qb.from_(bin)
			.from_(item)
			.from_(warehouse)
			.select(fn.Sum(bin.reserved_qty_for_sub_contract).as_("stock_qty"))
			.where(
				(warehouse.lft >= "lft")
				& (warehouse.rgt <= "rgt")
				& (item.name == bin.item_code)
				& (item.name == "item_code")
				& (warehouse.name == bin.warehouse)
				& (warehouse.up_purpose == "Storage")
			)
			.run(as_dict=True)
		)

		if stock_qty:
			stock_qty = adjust_qty_for_expired_items(item_code, stock_qty, warehouse)
			in_stock = stock_qty[0][0] > 0 and 1 or 0

	return frappe._dict(
		{"in_stock": in_stock, "stock_qty": stock_qty, "is_stock_item": is_stock_item}
	)
