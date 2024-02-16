// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports['Quotation Demand'] = {
	filters: [
		{
			fieldname: 'company',
			label: __('Company'),
			fieldtype: 'Link',
			options: 'Company',
		},
		{
			fieldname: 'start_date',
			label: __('Start Date'),
			fieldtype: 'Date',
		},
		{
			fieldname: 'end_date',
			label: __('End Date'),
			fieldtype: 'Date',
			default: moment(),
		},
		{
			fieldname: 'price_list',
			label: __('Price List'),
			fieldtype: 'Link',
			options: 'Price List',
		},
	],
	// get_datatable_options(options) {
	// 	return Object.assign(options, {
	// 		treeView: true,
	// 		checkedRowStatus: false,
	// 		checkboxColumn: true,
	// 		events: {
	// 			onCheckRow: row => {
	// 				update_selection(row)
	// 			},
	// 		},
	// 	})
	// },
	// onload: reportview => {
	// 	manage_buttons(reportview)
	// },
	// refresh: reportview => {
	// 	manage_buttons(reportview)
	// },
}
