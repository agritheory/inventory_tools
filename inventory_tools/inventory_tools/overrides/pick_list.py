from typing import TYPE_CHECKING

import frappe
from frappe.utils import safe_json_loads

if TYPE_CHECKING:
	from erpnext.stock.doctype.pick_list_item.pick_list_item import PickListItem
	from erpnext.stock.doctype.pick_list.pick_list import PickList


@frappe.whitelist()
def optimize_path(doc: "PickList", strategy: str) -> list["PickListItem"]:
	doc = safe_json_loads(doc) if isinstance(doc, str) else doc
	print("path button")
	return doc.locations
	# returns a list of Pick List Item in the correct order
