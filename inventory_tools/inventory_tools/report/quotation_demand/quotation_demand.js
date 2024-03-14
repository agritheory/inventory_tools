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
	],
	on_report_render: reportview => {
		reportview.datatable.options.columns[7].editable = true
		reportview.render_datatable()
		// these don't seem to be working
		$(".btn-default:contains('Create Card')").addClass('hidden')
		$(".btn-default:contains('Set Chart')").addClass('hidden')
	},
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
	reportview.page.add_inner_button(
		__('Create SO(s)'),
		function () {
			create()
		},
		__('Create')
	)
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

async function create() {
	let filters = frappe.query_report.get_filter_values()
	values = await select_company()
	company = values['company']
	warehouse = values['warehouse']
	let selected_rows = frappe.query_report.datatable.rowmanager.getCheckedRows()
	let selected_items = frappe.query_report.datatable.datamanager.data.filter((row, index) => {
		return selected_rows.includes(String(index)) && row.indent == 1 ? row : false
	})

	// Update split_qty with the edited value
	let selected_raw_rows = frappe.query_report.datatable.datamanager.rows.filter((row, index) => {
		return selected_rows.includes(String(index)) && row[0]['indent'] == 1 ? row : false
	})
	for (let i = 0; i < selected_items.length; i++) {
		selected_items[i]['split_qty'] = selected_raw_rows[i][9].content
	}

	if (!selected_items.length) {
		frappe.show_alert({ message: __('Please select one or more rows.'), seconds: 5, indicator: 'red' })
	} else {
		await frappe
			.xcall('inventory_tools.inventory_tools.report.quotation_demand.quotation_demand.create', {
				company: company || '',
				warehouse: warehouse || '',
				filters: filters,
				rows: selected_items,
			})
			.then(r => {})
	}
}

async function select_company() {
	return new Promise(resolve => {
		let dialog = new frappe.ui.Dialog({
			title: __('Select a Company'),
			fields: [
				{
					fieldtype: 'Link',
					fieldname: 'company',
					label: 'Company',
					options: 'Company',
					reqd: 0,
					description: __('Leave this field blank to disallow aggregation for this company'),
					change: () => {
						if (dialog.fields_dict.company.value) {
							dialog.fields_dict.warehouse.df.hidden = 0
							dialog.fields_dict.warehouse.df.reqd = 1
						} else {
							dialog.fields_dict.warehouse.df.hidden = 1
							dialog.fields_dict.warehouse.df.reqd = 0
						}
						dialog.refresh()
					},
				},
				{
					fieldtype: 'Link',
					fieldname: 'warehouse',
					label: 'Warehouse',
					options: 'Warehouse',
					reqd: 0,
					hidden: 1,
					get_query: function () {
						let company = dialog.get_value('company')
						if (company) {
							return {
								filters: { company: company },
							}
						}
					},
				},
			],
			primary_action: () => {
				let values = dialog.get_values()
				dialog.hide()
				return resolve(values)
			},
			primary_action_label: __('Select'),
		})
		dialog.show()
		dialog.get_close_btn()
	})
}
