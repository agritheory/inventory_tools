frappe.ui.form.on('Operation', {
	refresh: frm => {
		frm.trigger('workstation')
	},
	workstation: frm => {
		cur_frm.fields_dict.custom_alternative_workstations.get_query = function (doc) {
			return {
				filters: {
					workstation_name: ['!=', frm.doc.workstation],
				},
			}
		}
	},
})
