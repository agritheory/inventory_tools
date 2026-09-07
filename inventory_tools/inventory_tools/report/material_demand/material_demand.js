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
		show_aggregation_banner(reportview)
		manage_buttons(reportview)
	},
	refresh: reportview => {
		show_aggregation_banner(reportview)
		manage_buttons(reportview)
	},
}

function aggregation_settings() {
	const all = frappe.boot.inventory_tools_settings || {}
	for (const company of Object.keys(all)) {
		const settings = all[company]
		if (settings && settings.purchase_order_aggregation_company) {
			return settings
		}
	}
	return null
}

function show_aggregation_banner(reportview) {
	const settings = aggregation_settings()
	let sub_heading = $(reportview.$page.find('.sub-heading')[0])
	sub_heading.find('.material-demand-aggregation-banner').remove()
	if (!settings) {
		return
	}
	sub_heading.removeClass('hide')
	let message = __('Purchase Orders will be created for {0}.', [settings.purchase_order_aggregation_company])
	if (settings.aggregated_purchasing_warehouse) {
		message += ' ' + __('Items will be received into {0}.', [settings.aggregated_purchasing_warehouse])
	}
	sub_heading.append(`<span class="material-demand-aggregation-banner">${message}</span>`)
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

	// these don't seem to be working
	$(".btn-default:contains('Create Card')").addClass('hidden')
	$(".btn-default:contains('Set Chart')").addClass('hidden')
}

function selected_report_rows() {
	let selected_rows = frappe.query_report.datatable.rowmanager.getCheckedRows()
	return frappe.query_report.datatable.datamanager.data.filter((row, index) => {
		return selected_rows.includes(String(index)) ? row : false
	})
}

async function create(type) {
	const filters = frappe.query_report.get_filter_values()
	const selected_items = selected_report_rows()
	if (!selected_items.length) {
		frappe.show_alert({ message: 'Please select one or more rows.', seconds: 5, indicator: 'red' })
		return
	}

	const selection = await select_companies(filters.company, selected_items, type != 'po')
	if (!selection) {
		return
	}

	await frappe.xcall('inventory_tools.inventory_tools.report.material_demand.material_demand.create', {
		company: selection.company,
		companies: selection.companies,
		email_template: selection.email_template || '',
		filters: filters,
		creation_type: type,
		rows: selected_items,
	})
}

async function select_companies(filter_company, selected_items, include_email_template) {
	const mr_names = [...new Set((selected_items || []).map(row => row.material_request).filter(Boolean))]
	const company_by_mr = {}
	if (mr_names.length) {
		const mrs = await frappe.db.get_list('Material Request', {
			filters: { name: ['in', mr_names] },
			fields: ['name', 'company'],
			limit: mr_names.length,
		})
		for (const mr of mrs || []) {
			company_by_mr[mr.name] = mr.company
		}
	}
	for (const row of selected_items || []) {
		if (row.material_request && company_by_mr[row.material_request]) {
			row.company = company_by_mr[row.material_request]
		}
	}
	const available = [...new Set((selected_items || []).map(row => row.company).filter(Boolean))]
	const defaults = filter_company ? [filter_company] : available
	const settings = aggregation_settings()

	return new Promise(resolve => {
		let fields = [
			{
				fieldtype: 'MultiSelectList',
				fieldname: 'companies',
				label: __('Companies'),
				reqd: 1,
				get_data: function (txt) {
					return available
						.filter(company => !txt || company.toLowerCase().includes(String(txt).toLowerCase()))
						.map(company => ({ value: company, description: '' }))
				},
			},
		]
		if (settings) {
			let note = __('Purchase Orders will be created for {0}.', [settings.purchase_order_aggregation_company])
			if (settings.aggregated_purchasing_warehouse) {
				note += ' ' + __('Items will be received into {0}.', [settings.aggregated_purchasing_warehouse])
			}
			fields.unshift({
				fieldtype: 'HTML',
				fieldname: 'aggregation_note',
				options: `<p class="text-muted">${note}</p>`,
			})
		}
		if (include_email_template) {
			fields.push({
				fieldtype: 'Link',
				fieldname: 'email_template',
				label: 'Email Template',
				options: 'Email Template',
				reqd: 1,
			})
		}
		let dialog = new frappe.ui.Dialog({
			title: include_email_template ? __('Select Companies and Email Template') : __('Select Companies'),
			fields: fields,
			primary_action: () => {
				let values = dialog.get_values()
				if (!values.companies || !values.companies.length) {
					frappe.msgprint(__('Please select one or more companies.'))
					return
				}
				dialog.hide()
				return resolve({
					companies: values.companies,
					email_template: values.email_template,
					company: values.companies[0],
				})
			},
			primary_action_label: __('Create'),
		})
		dialog.show()
		dialog.set_value('companies', defaults)
		dialog.get_close_btn().on('click', () => resolve(null))
	})
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

/* jscpd:ignore-start */
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
/* jscpd:ignore-end */
