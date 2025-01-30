// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Dimension', {
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

	us_pallet_cases_per_level(frm) {
		frm.trigger('calculate_us_pallet_cases')
	},

	us_pallet_levels(frm) {
		frm.trigger('calculate_us_pallet_cases')
	},

	euro_pallet_cases_per_level(frm) {
		frm.trigger('calculate_euro_pallet_cases')
	},

	euro_pallet_levels(frm) {
		frm.trigger('calculate_euro_pallet_cases')
	},

	calculate_item_volume(frm) {
		frm.set_value('item_volume', frm.doc.item_length * frm.doc.item_width * frm.doc.item_height)
	},

	calculate_case_volume(frm) {
		frm.set_value('case_volume', frm.doc.case_length * frm.doc.case_width * frm.doc.case_height)
	},

	calculate_us_pallet_cases(frm) {
		frm.set_value('us_pallet_cases', frm.doc.us_pallet_cases_per_level * frm.doc.us_pallet_levels)
	},

	calculate_euro_pallet_cases(frm) {
		frm.set_value('euro_pallet_cases', frm.doc.euro_pallet_cases_per_level * frm.doc.euro_pallet_levels)
	},
})
