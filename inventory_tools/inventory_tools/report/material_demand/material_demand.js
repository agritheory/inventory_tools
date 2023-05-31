// Copyright (c) 2023, AgriTheory and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports['Material Demand'] = {
	filters: [
		// {
		// 	fieldname: 'price_list',
		// 	label: __('Price List'),
		// 	fieldtype: 'Link',
		// 	options: 'Price List',
		// 	reqd: 1,
		// 	default: 'Standard Buying',
		// 	// only buying price lists?
		// },
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
	],
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		})
	},
	onload: reportview => {
		manage_buttons(reportview)
	},
	refresh: reportview => {
		manage_buttons(reportview)
	},
}

function manage_buttons(reportview) {
	reportview.page.set_primary_action('Create PO(s)', () => {
		create_pos()
	})
	// these don't seem to be working
	$(".btn-default:contains('Create Card')").addClass('hidden')
	$(".btn-default:contains('Set Chart')").addClass('hidden')
}

async function create_pos() {
	let selected_rows = frappe.query_report.datatable.rowmanager.getCheckedRows()
	let selected_items = frappe.query_report.datatable.datamanager.data.filter((row, index) => {
		return selected_rows.includes(String(index)) ? row : false
	})
	if (!selected_items.length) {
		frappe.show_alert({ message: 'Please select one or more rows.', seconds: 5, indicator: 'red' })
	} else {
		await frappe
			.xcall('hausers.hausers.report.material_demand.material_demand.create_pos', {
				rows: selected_items,
			})
			.then(r => {})
	}
}
