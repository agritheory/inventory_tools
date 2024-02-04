// Copyright (c) 2023, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Specification Attribute', {
	applied_on: (frm, cdt, cdn) => {
		get_data_fieldnames(frm, cdt, cdn)
	},
	form_render: (frm, cdt, cdn) => {
		get_data_fieldnames(frm, cdt, cdn)
	},
})

function get_data_fieldnames(frm, cdt, cdn) {
	let row = locals[cdt][cdn]
	if (!row.applied_on) {
		return
	}
	frappe
		.xcall('inventory_tools.inventory_tools.doctype.specification.specification.get_data_fieldnames', {
			doctype: row.applied_on,
		})
		.then(r => {
			if (!r) {
				return
			}
			frm.set_df_property('attributes', 'options', r, frm.doc.name, 'field', row.name)
			frm.refresh_field('attributes')
		})
}
