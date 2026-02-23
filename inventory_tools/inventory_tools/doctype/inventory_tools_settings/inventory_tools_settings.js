// Copyright (c) 2023, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inventory Tools Settings', {
	onload(frm) {
		set_cartonization_doctype_filter(frm)
	},
	refresh(frm) {
		set_cartonization_doctype_filter(frm)
		frm.set_query('default_quarantine_warehouse', function () {
			return {
				filters: {
					company: frm.doc.company,
				},
			}
		})
	},
})

function set_cartonization_doctype_filter(frm) {
	const allowed_doctypes = ['Pick List', 'Stock Entry', 'Delivery Note', 'Packing Slip']

	frm.set_query('cartonization_doctypes', function () {
		return {
			filters: {
				name: ['in', allowed_doctypes],
			},
		}
	})
}
