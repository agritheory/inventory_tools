frappe.ui.form.on('Job Card', {
	operation: function (frm) {
		if (frm.doc.operation) {
			frappe.call({
				method: 'inventory_tools.api.get_alternative_workstations',
				args: {
					operation: frm.doc.operation,
				},
				callback: function (r) {
					frm.clear_table('custom_alternative_workstations')
					r.message.forEach(element => {
						if (element.workstation) {
							let row = frm.add_child('custom_alternative_workstations')
							row.workstation = element.workstation
						}
						frm.refresh_field('custom_alternative_workstations')
					})
				},
			})
		}
	},
})
