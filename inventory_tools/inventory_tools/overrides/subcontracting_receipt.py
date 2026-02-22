# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

from erpnext.subcontracting.doctype.subcontracting_receipt.subcontracting_receipt import (
	SubcontractingReceipt,
)

from inventory_tools.inventory_tools.overrides.inspection import (
	validate_inspection_with_company_scope,
)


class InventoryToolsSubcontractingReceipt(SubcontractingReceipt):
	def validate_inspection(self):
		validate_inspection_with_company_scope(self)
