// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.query_reports['Three Way Check'] = {
	filters: [
		{
			fieldname: 'company',
			label: __('Company'),
			fieldtype: 'Link',
			options: 'Company',
			reqd: true,
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
			reqd: true,
		},
		{
			fieldname: 'cycle',
			label: __('Cycle'),
			fieldtype: 'Select',
			options: ['Purchasing Cycle', 'Sales Cycle', 'Quotation Cycle'],
			default: 'Purchasing Cycle',
		},
	],
}
