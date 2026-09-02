// Copyright (c) 2023, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inventory Tools Settings', {
	onload(frm) {
		set_filters(frm)
	},
	refresh(frm) {
		set_filters(frm)
	},
})

function set_filters(frm) {
	frm.set_query('cartonization_doctypes', () => {
		const allowed_doctypes = ['Pick List', 'Stock Entry', 'Delivery Note', 'Packing Slip']
		return {
			filters: {
				name: ['in', allowed_doctypes],
			},
		}
	})
	frm.set_query('default_quarantine_warehouse', () => {
		return {
			filters: {
				company: frm.doc.company,
			},
		}
	})
	frm.set_query('aggregated_purchasing_warehouse', () => {
		return {
			filters: {
				company: frm.doc.purchase_order_aggregation_company,
				is_group: 0,
			},
		}
	})
}
