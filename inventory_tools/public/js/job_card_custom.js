// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Card', {
	refresh: frm => {
		if (frm.doc.operation) {
			set_workstation_query(frm)
		}
	},
	operation: frm => {
		set_workstation_query(frm)
	},
})

function set_workstation_query(frm) {
	frm.set_query('workstation', doc => {
		return {
			query: 'inventory_tools.inventory_tools.overrides.workstation.get_alternative_workstations',
			filters: {
				operation: doc.operation,
			},
		}
	})
}
