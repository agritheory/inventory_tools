// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

frappe.query_reports['Undeclared UOM'] = {
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
			fieldname: 'from_date',
			label: __('From Date'),
			fieldtype: 'Date',
			reqd: 1,
			default: frappe.datetime.year_start(),
		},
		{
			fieldname: 'to_date',
			label: __('To Date'),
			fieldtype: 'Date',
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: 'group_by',
			label: __('Group By'),
			fieldtype: 'Select',
			options: ['UOM Pair', 'Document'],
			default: 'UOM Pair',
			reqd: 1,
		},
		{
			fieldname: 'document_type',
			label: __('Document Type'),
			fieldtype: 'MultiSelectList',
			get_data: function (txt) {
				return frappe
					.call({
						method: 'inventory_tools.inventory_tools.report.undeclared_uom.undeclared_uom.get_document_type_options',
						args: { txt },
					})
					.then(r => r.message || [])
			},
		},
		{
			fieldname: 'item_code',
			label: __('Item'),
			fieldtype: 'Link',
			options: 'Item',
		},
		{
			fieldname: 'undeclared_uom',
			label: __('Undeclared UOM'),
			fieldtype: 'Link',
			options: 'UOM',
		},
		{
			fieldname: 'status',
			label: __('Status'),
			fieldtype: 'MultiSelectList',
			get_data: function () {
				return [
					{ value: 'Draft', description: '' },
					{ value: 'Submitted', description: '' },
					{ value: 'Cancelled', description: '' },
				]
			},
			default: 'Submitted',
		},
	],
	get_datatable_options(options) {
		return Object.assign(options, {
			treeView: true,
		})
	},
}
