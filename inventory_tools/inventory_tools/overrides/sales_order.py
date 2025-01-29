# Copyright (c) 2023, AgriTheory and Contributors
# See license.txt
import frappe
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder, WarehouseRequired
from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company
from frappe import _
from frappe.utils import cint


class InventoryToolsSalesOrder(SalesOrder):
	def validate_with_previous_doc(self):
		config = {"Quotation": {"ref_dn_field": "prevdoc_docname", "compare_fields": [["company", "="]]}}
		if self.multi_company_sales_order:
			config.pop("Quotation")
		super(SalesOrder, self).validate_with_previous_doc(config)

	def validate_warehouse(self):
		warehouses = list({d.warehouse for d in self.get("items") if getattr(d, "warehouse", None)})

		target_warehouses = list(
			{d.target_warehouse for d in self.get("items") if getattr(d, "target_warehouse", None)}
		)

		warehouses.extend(target_warehouses)

		from_warehouse = list(
			{d.from_warehouse for d in self.get("items") if getattr(d, "from_warehouse", None)}
		)

		warehouses.extend(from_warehouse)

		for w in warehouses:
			validate_disabled_warehouse(w)
			if not self.multi_company_sales_order:
				validate_warehouse_company(w, self.company)

		for d in self.get("items"):
			if (
				(
					frappe.get_cached_value("Item", d.item_code, "is_stock_item") == 1
					or (self.has_product_bundle(d.item_code) and self.product_bundle_has_stock_item(d.item_code))
				)
				and not d.warehouse
				and not cint(d.delivered_by_supplier)
			):
				frappe.throw(
					_("Delivery warehouse required for stock item {0}").format(d.item_code), WarehouseRequired
				)
