# Copyright(c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import frappe

from inventory_tools.inventory_tools.overrides.uom import get_uom_enforcement


def boot_session(bootinfo):
	bootinfo.inventory_tools = frappe._dict()
	bootinfo.inventory_tools.uom_enforcement = get_uom_enforcement()
