// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

frappe.query_reports['UOM Conversion Exceptions'] = {
	filters: [
		{
			fieldname: 'company',
			label: __('Company'),
			fieldtype: 'Link',
			options: 'Company',
			default: frappe.defaults.get_default('company'),
		},
		{
			fieldname: 'from_date',
			label: __('From Date'),
			fieldtype: 'Date',
		},
		{
			fieldname: 'to_date',
			label: __('To Date'),
			fieldtype: 'Date',
		},
		{
			fieldname: 'uom',
			label: __('UOM'),
			fieldtype: 'MultiSelectList',
			options: 'UOM',
			get_data: function (txt) {
				return frappe.db.get_link_options('UOM', txt)
			},
		},
		{
			fieldname: 'uom_category',
			label: __('UOM Category'),
			fieldtype: 'MultiSelectList',
			options: 'UOM Category',
			get_data: function (txt) {
				return frappe
					.call({
						method: 'inventory_tools.inventory_tools.uom_conversion_exceptions.category_filter_multiselect_data',
						args: { txt: txt || '' },
						type: 'POST',
					})
					.then(r => r.message || [])
			},
		},
	],
}
