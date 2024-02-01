frappe.ui.form.on('BOM', {
	refresh: function (frm) {
		frm.trigger('get_alternative_workstations')
	},
	operation: function (frm) {
		frm.trigger('get_alternative_workstations')
	},
	get_alternative_workstations: function (frm) {
		frm.set_query('workstation', 'operations', function (doc, cdt, cdn) {
			let d = locals[cdt][cdn]
			return {
				query: 'inventory_tools.api.get_alternative_workstations',
				filters: {
					operation: d.operation,
				},
			}
		})
	},
})
