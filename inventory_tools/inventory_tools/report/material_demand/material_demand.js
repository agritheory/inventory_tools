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
		{
			fieldname: 'price_list',
			label: __('Price List'),
			fieldtype: 'Link',
			options: 'Price List',
		},
	],
	on_report_render: reportview => {
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
		'Create PO(s)',
		function () {
			create('po')
		},
		'Create'
	)

	reportview.page.add_inner_button(
		'Create RFQ(s)',
		function () {
			create('rfq')
		},
		'Create'
	)

	reportview.page.add_inner_button(
		'Create based on Item',
		function () {
			create('item_based')
		},
		'Create'
	)
}

async function create(type) {
	let filters = frappe.query_report.get_filter_values()
	let company = undefined
	let email_template = undefined
	let warehouse = undefined

	if (type != 'po') {
		values = await select_company_and_email_template(values.company)
		company = values['company']
		email_template = values['email_template']
	} else {
		values = await select_company()
		company = values['company']
		warehouse = values['warehouse']
	}

	let selected_rows = frappe.query_report.datatable.rowmanager.getCheckedRows()
	let selected_items = frappe.query_report.datatable.datamanager.data.filter((row, index) => {
		return selected_rows.includes(String(index)) && row.indent == 1 ? row : false
	})
	if (!selected_items.length) {
		frappe.show_alert({ message: 'Please select one or more rows.', seconds: 5, indicator: 'red' })
	} else {
		await frappe
			.xcall('inventory_tools.inventory_tools.report.material_demand.material_demand.create', {
				company: company || '',
				warehouse: warehouse || '',
				email_template: email_template || '',
				filters: filters,
				creation_type: type,
				rows: selected_items,
			})
			.then(r => {})
	}
}

function update_selection(row) {
	if (row !== undefined && !row[5].content) {
		const toggle = frappe.query_report.datatable.rowmanager.checkMap[row[0].rowIndex]
		select_all_supplier_items(row, toggle).then(() => {
			update_selected_qty()
		})
	} else {
		update_selected_qty()
	}
}

function update_selected_qty() {
	// iterate all rows for selected items
	let item_map = {}
	frappe.query_report.datatable.datamanager.data.forEach((supplier_row, index) => {
		if (frappe.query_report.datatable.rowmanager.checkMap[index]) {
			if (supplier_row.item_code && !item_map[supplier_row.item_code]) {
				item_map[supplier_row.item_code] = supplier_row.qty
			} else if (supplier_row.item_code && item_map[supplier_row.item_code]) {
				item_map[supplier_row.item_code] += supplier_row.qty
			}
		}
	})
	frappe.query_report.datatable.datamanager.data.forEach((supplier_row, index) => {
		if (supplier_row.item_code in item_map) {
			let supplier_price = Number(String(supplier_row.supplier_price).replace(/[^0-9\.-]+/g, ''))
			let total_selected = item_map[supplier_row.item_code]
			let selected_price = item_map[supplier_row.item_code] * (supplier_price || 0)
			selected_price = format_currency(selected_price, supplier_row.currency, 2)
			if (item_map[supplier_row.item_code] > supplier_row.total_demand) {
				total_selected = `<span style="color: red">${total_selected}</span>`
				selected_price = `<span style="color: red">${selected_price}</span>`
			}
			frappe.query_report.datatable.cellmanager.updateCell(9, index, total_selected, true)
			frappe.query_report.datatable.cellmanager.updateCell(12, index, selected_price, true)
		} else {
			frappe.query_report.datatable.cellmanager.updateCell(9, index, '', true)
			frappe.query_report.datatable.cellmanager.updateCell(12, index, '', true)
		}
	})
}

async function select_all_supplier_items(row, toggle) {
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

async function select_company() {
	return new Promise(resolve => {
		let dialog = new frappe.ui.Dialog({
			title: __('Aggregate by Company'),
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

async function select_company_and_email_template(company) {
	return new Promise(resolve => {
		let dialog = new frappe.ui.Dialog({
			title: __('Select Company and Email Template'),
			fields: [
				{
					fieldtype: 'Link',
					fieldname: 'company',
					label: 'Company',
					options: 'Company',
					reqd: 1,
					default: company,
				},
				{
					fieldtype: 'Link',
					fieldname: 'email_template',
					label: 'Email Template',
					options: 'Email Template',
					reqd: 1,
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
