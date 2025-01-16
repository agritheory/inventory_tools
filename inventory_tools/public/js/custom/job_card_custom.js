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
				operation: frm.doc.operation,
				company: frm.doc.company,
			},
		}
	})
}
