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
					is_group: 1,
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
		} else if (column.fieldname == 'per_picked' && data && data.per_picked !== null) {
			if (data.per_picked == 100) {
				value = "<span style='color:green'>" + value + '</span>'
			} else {
				value = "<span style='color:red'>" + value + '</span>'
			}
		} else if (column.fieldname == 'total_stock' && data && data.total_stock !== null) {
			if (data.total_stock == 'Total Availability') {
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
		report.page.add_inner_button(
			__('Pick List'),
			function () {
				create_pick_list()
			},
			__('Create')
		)
		report.page.add_inner_button(
			__('Pick List & Delivery Note'),
			function () {
				create_pick_list_delivery_note()
			},
			__('Create')
		)
	},
}

async function check_stock() {
	let values = frappe.query_report.get_filter_values()
	await frappe
		.xcall('inventory_tools.inventory_tools.report.pick_list_tool.pick_list_tool.check_stock', {
			filters: values,
		})
		.then(r => {})
}
function print_pick() {
	if (!frappe.query_report.filters || frappe.query_report.get_filter_value('status') != 'Already Picked') {
		frappe.msgprint('Only can print Already Picked')
		return
	}
}

function create_pick_list() {}
function create_pick_list_delivery_note() {}
