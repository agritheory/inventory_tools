# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote

from inventory_tools.inventory_tools.overrides.inspection import (
	validate_inspection_with_company_scope,
)


class InventoryToolsDeliveryNote(DeliveryNote):
	def validate_inspection(self):
		validate_inspection_with_company_scope(self)
