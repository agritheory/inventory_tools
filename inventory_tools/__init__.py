# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

__version__ = "15.20.0"

import erpnext.stock.get_item_details
import frappe
from frappe import _
from frappe.utils import cint

original_validate_item_details = erpnext.stock.get_item_details.validate_item_details
original_insert_item_price = erpnext.stock.get_item_details.insert_item_price


def is_generic_item(item_code) -> bool:
	try:
		return bool(frappe.get_cached_value("Item", item_code, "is_generic_item"))
	except Exception:
		return False


def work_order_subcontracting_enabled(company) -> bool:
	try:
		return bool(
			frappe.db.get_value(
				"Inventory Tools Settings",
				{"company": company},
				"enable_work_order_subcontracting",
			)
		)
	except Exception:
		return False


def patched_validate_item_details(args, item):
	"""
	APP: inventory_tools HASH: a1676c3b47ef16a39e9333ae41ad82f8c63a5fb4 REPO: https://github.com/frappe/erpnext PATH: erpnext/stock/get_item_details.py METHOD: validate_item_details
	"""
	if not args.company:
		frappe.throw(_("Please specify Company"))

	from erpnext.stock.doctype.item.item import validate_end_of_life

	validate_end_of_life(item.name, item.end_of_life, item.disabled)

	if cint(item.has_variants):
		msg = f"Item {item.name} is a template, please select one of its variants"

		frappe.throw(_(msg), title=_("Template Item Selected"))

	elif args.transaction_type == "buying" and args.doctype != "Material Request":
		if not work_order_subcontracting_enabled(args.company):
			if args.get("is_subcontracted"):
				if args.get("is_old_subcontracting_flow"):
					if item.is_sub_contracted_item != 1:
						frappe.throw(_("Item {0} must be a Sub-contracted Item").format(item.name))
				else:
					if item.is_stock_item:
						frappe.throw(_("Item {0} must be a Non-Stock Item").format(item.name))


def patched_insert_item_price(args):
	"""
	APP: inventory_tools HASH: de2a363416328242f3ae6fd14a12587047285754 REPO: https://github.com/frappe/erpnext PATH: erpnext/stock/get_item_details.py METHOD: insert_item_price
	"""
	if args.get("item_code") and is_generic_item(args.item_code):
		return
	return original_insert_item_price(args)


erpnext.stock.get_item_details.validate_item_details = patched_validate_item_details
erpnext.stock.get_item_details.insert_item_price = patched_insert_item_price
