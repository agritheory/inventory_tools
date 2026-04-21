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
		{
			fieldname: 'purchase_order',
			label: __('Purchase Order'),
			fieldtype: 'Link',
			options: 'Purchase Order',
			depends_on: "eval:doc.cycle=='Purchasing Cycle'",
		},
		{
			fieldname: 'purchase_receipt',
			label: __('Purchase Receipt'),
			fieldtype: 'Link',
			options: 'Purchase Receipt',
			depends_on: "eval:doc.cycle=='Purchasing Cycle'",
		},
		{
			fieldname: 'purchase_invoice',
			label: __('Purchase Invoice'),
			fieldtype: 'Link',
			options: 'Purchase Invoice',
			depends_on: "eval:doc.cycle=='Purchasing Cycle'",
		},
		{
			fieldname: 'sales_order',
			label: __('Sales Order'),
			fieldtype: 'Link',
			options: 'Sales Order',
			depends_on: "eval:doc.cycle=='Sales Cycle'",
		},
		{
			fieldname: 'delivery_note',
			label: __('Delivery Note'),
			fieldtype: 'Link',
			options: 'Delivery Note',
			depends_on: "eval:doc.cycle=='Sales Cycle'",
		},
		{
			fieldname: 'sales_invoice',
			label: __('Sales Invoice'),
			fieldtype: 'Link',
			options: 'Sales Invoice',
			depends_on: "eval:doc.cycle=='Sales Cycle'",
		},
		{
			fieldname: 'request_for_quotation',
			label: __('Request for Quotation'),
			fieldtype: 'Link',
			options: 'Request for Quotation',
			depends_on: "eval:doc.cycle=='Quotation Cycle'",
		},
		{
			fieldname: 'supplier_quotation',
			label: __('Supplier Quotation'),
			fieldtype: 'Link',
			options: 'Supplier Quotation',
			depends_on: "eval:doc.cycle=='Quotation Cycle'",
		},
		{
			fieldname: 'purchase_order_quotation',
			label: __('Purchase Order'),
			fieldtype: 'Link',
			options: 'Purchase Order',
			depends_on: "eval:doc.cycle=='Quotation Cycle'",
		},
	],
}
