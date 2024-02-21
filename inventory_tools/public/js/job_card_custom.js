frappe.ui.form.on('Job Card', {
	refresh: frm => {
		set_workstation_query(frm)
	},
	operation: frm => {
		set_workstation_query(frm)
	},
})

function set_workstation_query(frm) {
	if (!frm.doc.operation) {
		frappe.throw('Please select a Operation first.')
	}
	frm.set_query('workstation', doc => {
		return {
			query: 'inventory_tools.inventory_tools.overrides.workstation.get_alternative_workstations',
			filters: {
				operation: doc.operation,
			},
		}
	})
}
