import frappe
from erpnext.stock.doctype.pick_list.pick_list import PickList
from erpnext.stock.doctype.pick_list_item.pick_list_item import PickListItem
from frappe.utils import safe_json_loads


@frappe.whitelist()
def optimize_path(doc: PickList, strategy: str) -> [PickListItem]:
	doc = safe_json_loads(doc) if isinstance(doc, str) else doc
	print("path button")
	# returns a list of Pick List Item in the correct order
