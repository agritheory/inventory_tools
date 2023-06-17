// Copyright (c) 2023, AgriTheory and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports['Material Demand'] = {
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
			.xcall('inventory_tools.inventory_tools.report.material_demand.material_demand.create_pos', {
				rows: selected_items,
			})
			.then(r => {})
	}
}

function update_selection(row) {
	if (!row[5]) {
		// const checked = true //frappe.query_report.datatable.rowmanager.checkMap[row.rowIndex]
		// // console.log(checked)
		// frappe.query_report.datatable.datamanager.data.forEach((supplier_row, index) => {
		// 	if(supplier_row.supplier === row[2].content){
		// 		frappe.query_report.datatable.rowmanager.checkMap.splice(index, 1, checked)
		// 	}
		// })
	} else {
		// this should be a standalone function
		// update selected_qty, format red if its over demand qty
		update_selected_qty(row)
	}
}

function update_selected_qty(row) {
	const checked = frappe.query_report.datatable.rowmanager.checkMap[row[0].rowIndex]
	let total_item_qty = 0.0
	frappe.query_report.datatable.datamanager.data.forEach((supplier_row, index) => {
		if (supplier_row.item_code === row[5].content) {
			if (checked) {
				total_item_qty += supplier_row.qty
			}
		}
	})
	console.log(total_item_qty)
	// frappe.query_report.datatable.datamanager.data.forEach((supplier_row, index) => {
	// 	if (supplier_row.item_code === row[5].content) {
	// 		if (checked) {
	// 			console.log('total', total_item_qty)
	// 		}
	// 	}
	// })
}
