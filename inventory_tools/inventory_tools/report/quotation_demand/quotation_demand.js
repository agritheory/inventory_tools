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
	get_datatable_options(options) {
		return Object.assign(options, {
			treeView: true,
			checkedRowStatus: false,
			checkboxColumn: true,
			events: {
				onCheckRow: row => {
					update_selection(row)
				},
			},
		})
	},
}

function update_selection(row) {
	if (row !== undefined && !row[5].content) {
		const toggle = frappe.query_report.datatable.rowmanager.checkMap[row[0].rowIndex]
		select_all_customer_items(row, toggle)
	}
}

async function select_all_customer_items(row, toggle) {
	return new Promise(resolve => {
		if (frappe.query_report.datatable.datamanager._filteredRows) {
			frappe.query_report.datatable.datamanager._filteredRows.forEach(f => {
				if (f[2].content === row[1].content) {
					frappe.query_report.datatable.rowmanager.checkMap.splice(row[0].rowIndex, 0, toggle ? 1 : 0)
					$(row[0].content).find('input').check = toggle
				} else {
					frappe.query_report.datatable.rowmanager.checkMap.splice(f[0].rowIndex, 0, 0)
				}
			})
		} else {
			frappe.query_report.datatable.datamanager.rows.forEach(f => {
				if (f[2].content === row[2].content) {
					frappe.query_report.datatable.rowmanager.checkMap.splice(row[0].rowIndex, 0, toggle ? 1 : 0)
					let input = $(frappe.query_report.datatable.rowmanager.getRow$(f[0].rowIndex)).find('input')
					if (input[0]) {
						input[0].checked = toggle
					}
				} else {
					frappe.query_report.datatable.rowmanager.checkMap.splice(f[0].rowIndex, 0, 0)
				}
			})
		}
		resolve()
	})
}
