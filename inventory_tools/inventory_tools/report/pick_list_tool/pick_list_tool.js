// Copyright (c) 2023, AgriTheory and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports['Pick List Tool'] = {
	filters: [
		{
			fieldname: 'company',
			label: __('Company'),
			fieldtype: 'Link',
			options: 'Company',
			default: frappe.defaults.get_user_default('Company'),
			reqd: 1,
		},
		{
			fieldname: 'status',
			label: __('Status'),
			fieldtype: 'Select',
			options: ['', 'Already Picked', 'Not Picked', 'Unshipped'],
		},
		{
			fieldname: 'delivery_date_start',
			label: __('Delivery Date (start)'),
			fieldtype: 'Date',
		},
		{
			fieldname: 'delivery_date_end',
			label: __('Delivery Date (end)'),
			fieldtype: 'Date',
		},
		{
			fieldname: 'warehouse',
			label: __('Warehouse'),
			fieldtype: 'MultiSelectList',
			options: 'Warehouse',
			get_data: function (txt) {
				return frappe.db.get_link_options('Warehouse', txt, {
					company: frappe.query_report.get_filter_value('company'),
				})
			},
		},
		{
			fieldname: 'customer',
			label: __('Customer'),
			fieldtype: 'Link',
			options: 'Customer',
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data)
		if (column.fieldname == 'sales_order' && data && data.sales_order) {
			value = value.bold()
		} else if (column.fieldname == 'picked_percentage' && data && data.picked_percentage) {
			if (data.picked_percentage == 100) {
				value = "<span style='color:green'>" + value + '</span>'
			} else {
				value = "<span style='color:red'>" + value + '</span>'
			}
		}
		return value
	},
	onload: report => {
		report.page.add_button('Check Stock', () => {
			check_stock()
		})
		report.page.add_button('Print Pick', () => {
			print_pick()
		})
		report.page.add_inner_button(__('Pick List'), function () {}, __('Create'))
		report.page.add_inner_button(__('Pick List & Delivery Note'), function () {}, __('Create'))
	},
}

function check_stock() {}
function print_pick() {}
