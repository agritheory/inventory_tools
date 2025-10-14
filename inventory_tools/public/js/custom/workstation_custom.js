// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Workstation', {
	setup: frm => {},
	onload(frm) {
		;['electricity_cost', 'consumable_cost', 'rent_cost', 'wages', 'net_hour_rate'].forEach(field => {
			frm.set_df_property(field, 'read_only', 1)
		})
	},
})

frappe.ui.form.on('Workstation Working Hour', {
	shift_type: (frm, cdt, cdn) => {
		row = locals[cdt][cdn]
		if (!row.shift_type) {
			return
		}
		frappe.db.get_value('Shift Type', row.shift_type, ['start_time', 'end_time']).then(r => {
			frappe.model.set_value(row.doctype, row.name, 'start_time', r.message.start_time)
			frappe.model.set_value(row.doctype, row.name, 'end_time', r.message.end_time)
		})
	},
})
