// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Physical Dimension', {
	refresh(frm) {
		frm.set_query('reference_doctype', () => ({
			filters: {
				name: ['in', ['Item', 'Vehicle', 'Warehouse', 'Workstation']],
			},
		}))
	},

	item_height(frm) {
		frm.trigger('calculate_item_volume')
	},

	item_length(frm) {
		frm.trigger('calculate_item_volume')
	},

	item_width(frm) {
		frm.trigger('calculate_item_volume')
	},

	case_height(frm) {
		frm.trigger('calculate_case_volume')
	},

	case_length(frm) {
		frm.trigger('calculate_case_volume')
	},

	case_width(frm) {
		frm.trigger('calculate_case_volume')
	},

	calculate_item_volume(frm) {
		frm.set_value('item_volume', frm.doc.item_length * frm.doc.item_width * frm.doc.item_height)
	},

	calculate_case_volume(frm) {
		frm.set_value('case_volume', frm.doc.case_length * frm.doc.case_width * frm.doc.case_height)
	},
})
