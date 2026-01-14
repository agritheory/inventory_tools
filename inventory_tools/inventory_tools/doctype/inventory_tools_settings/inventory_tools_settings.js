// Copyright (c) 2023, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inventory Tools Settings', {
	refresh: function (frm) {
		frm.set_query('default_quarantine_warehouse', function () {
			return {
				filters: {
					company: frm.doc.company,
				},
			}
		})
	},
})
