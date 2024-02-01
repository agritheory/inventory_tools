frappe.ui.form.on('Job Card', {
	refresh: function (frm) {
		frm.trigger('get_alternative_workstations')
	},
	operation: function (frm) {
		frm.trigger('get_alternative_workstations')
	},
	get_alternative_workstations: function (frm) {
		frm.set_query('workstation', function (doc, cdt, cdn) {
			return {
				query: 'inventory_tools.api.get_alternative_workstations',
				filters: {
					operation: frm.doc.operation,
				},
			}
		})
	},
})
