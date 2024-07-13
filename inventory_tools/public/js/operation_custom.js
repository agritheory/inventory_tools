// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Operation', {
	refresh: frm => {
		get_filter_workstations(frm)
	},
	workstation: frm => {
		get_filter_workstations(frm)
	},
})

function get_filter_workstations(frm) {
	cur_frm.fields_dict.alternative_workstations.get_query = function (doc) {
		return {
			filters: {
				workstation_name: ['!=', frm.doc.workstation],
			},
		}
	}
}
