# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

# inventory_tools/patches/monkey_patches.py


def apply_operating_cost_patches():
	"""
	Monkey patch ERPNext functions at app load.
	"""
	from erpnext.stock.doctype.stock_entry import stock_entry
	from inventory_tools.inventory_tools.doctype.workstation_operating_cost.workstation_operating_cost import (
		get_operating_cost_per_unit_with_date_range,
	)

	# Replace ERPNext's original function
	stock_entry.get_operating_cost_per_unit = get_operating_cost_per_unit_with_date_range
