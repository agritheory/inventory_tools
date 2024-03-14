# Copyright (c) 2023, AgriTheory and Contributors
# See license.txt
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder


class InventoryToolsSalesOrder(SalesOrder):
	def validate_with_previous_doc(self):
		config = {"Quotation": {"ref_dn_field": "prevdoc_docname", "compare_fields": [["company", "="]]}}
		if self.multi_company_sales_order:
			config.pop("Quotation")
		super(SalesOrder, self).validate_with_previous_doc(config)
