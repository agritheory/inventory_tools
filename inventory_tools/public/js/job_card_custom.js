frappe.ui.form.on('Job Card', {
	refresh: frm => {
		frm.trigger('set_workstation')
	},
	operation: frm => {
		frm.trigger('set_workstation')
	},
	set_workstation: frm => {
		frm.set_query("workstation", function(doc) {
			return {
				query: "inventory_tools.api.get_alternative_workstations",
				filters: {
					operation: frm.doc.operation
				}
			};
		});
	}
})
