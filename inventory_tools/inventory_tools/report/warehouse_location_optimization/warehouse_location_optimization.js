// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

frappe.query_reports['Warehouse Location Optimization'] = {
	filters: [
		{
			fieldname: 'company',
			label: __('Company'),
			fieldtype: 'Link',
			options: 'Company',
			reqd: 1,
			default: frappe.defaults.get_user_default('Company'),
		},
		{
			fieldname: 'warehouse_plan',
			label: __('Warehouse Plan'),
			fieldtype: 'Link',
			options: 'Warehouse Plan',
			reqd: 1,
			get_query: () => {
				const company = frappe.query_report.get_filter_value('company')
				return company ? { filters: { company } } : {}
			},
		},
		{
			fieldname: 'warehouse',
			label: __('Warehouse'),
			fieldtype: 'Link',
			options: 'Warehouse',
			get_query: () => {
				const company = frappe.query_report.get_filter_value('company')
				return company ? { filters: { company, is_group: 1 } } : {}
			},
		},
		{
			fieldname: 'from_date',
			label: __('From Date'),
			fieldtype: 'Date',
			reqd: 1,
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -90),
		},
		{
			fieldname: 'to_date',
			label: __('To Date'),
			fieldtype: 'Date',
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
	],
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
			checkedRowStatus: false,
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
	reportview.page.add_inner_button(__('Set Default Warehouse'), () => apply_action('default'), __('Apply'))
	reportview.page.add_inner_button(__('Create Putaway Rule'), () => apply_action('putaway'), __('Apply'))
}

function get_selected_rows() {
	const selected_indexes = frappe.query_report.datatable.rowmanager.getCheckedRows()
	return frappe.query_report.datatable.datamanager.data.filter((row, index) => selected_indexes.includes(String(index)))
}

async function apply_action(action) {
	const rows = get_selected_rows()
	if (!rows.length) {
		frappe.show_alert({
			message: __('Please select one or more rows.'),
			indicator: 'red',
		})
		return
	}

	const missing_suggestion = rows.filter(row => !row.suggested_warehouse)
	if (missing_suggestion.length) {
		frappe.show_alert({
			message: __('All selected rows must have a suggested warehouse.'),
			indicator: 'red',
		})
		return
	}

	if (action === 'default') {
		const { company } = frappe.query_report.get_filter_values()
		await frappe.xcall(
			'inventory_tools.inventory_tools.report.warehouse_location_optimization.warehouse_location_optimization.set_default_warehouses',
			{ rows, company }
		)
		frappe.show_alert({
			message: __('Default warehouse updated for selected items.'),
			indicator: 'green',
		})
		frappe.query_report.refresh()
		return
	}

	const missing_capacity = rows.filter(row => !flt(row.capacity))
	if (missing_capacity.length) {
		frappe.show_alert({
			message: __(
				'All selected rows need slot capacity. Add item exterior and warehouse interior dimensions, then refresh the report.'
			),
			indicator: 'red',
		})
		return
	}

	await frappe.xcall(
		'inventory_tools.inventory_tools.report.warehouse_location_optimization.warehouse_location_optimization.create_putaway_rules',
		{ rows }
	)
	frappe.show_alert({
		message: __('Putaway rules created or updated for selected items.'),
		indicator: 'green',
	})
	frappe.query_report.refresh()
}
