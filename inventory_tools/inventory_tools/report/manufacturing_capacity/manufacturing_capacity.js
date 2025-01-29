// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports['Manufacturing Capacity'] = {
	filters: [
		{
			fieldname: 'bom',
			label: __('BOM'),
			fieldtype: 'Link',
			options: 'BOM',
			reqd: 1,
		},
		{
			fieldname: 'warehouse',
			label: __('Warehouse'),
			fieldtype: 'Link',
			options: 'Warehouse',
			reqd: 1,
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data)

		if (data && data.is_selected_bom) {
			value = value.bold()
		}
		return value
	},
}
