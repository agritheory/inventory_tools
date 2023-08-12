__version__ = "14.0.1"

import erpnext.stock.get_item_details

from inventory_tools.inventory_tools.overrides.purchase_order import validate_item_details

erpnext.stock.get_item_details.validate_item_details = validate_item_details
