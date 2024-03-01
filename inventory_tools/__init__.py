__version__ = "14.3.0"


"""
This code loads a modified version of validate_item_details function. It's called from
get_item_details, which is a whitelisted method called both client-side as well as
server-side (in validation functions) for several doctypes. Because of the dual nature,
two methods were needed to ensure the correct code runs in all scenarios: the standard
override whitelisted method in hooks.py and the monkey patch below.

The modification only applies when the Enable Work Order Subcontracting feature is selected in
Inventory Tools Settings. If the feature is turned off, the default ERPNext behavior runs.
"""
import erpnext.stock.get_item_details

from inventory_tools.inventory_tools.overrides.purchase_order import validate_item_details

erpnext.stock.get_item_details.validate_item_details = validate_item_details
