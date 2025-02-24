// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pick List', {
	refresh: frm => {
		add_path_button(frm)
	},
})

function add_path_button(frm) {
	frm.add_custom_button(__('Optimize Path'), () => {
		path_dialog(frm)
	})
}

function path_dialog(frm) {
	let d = new frappe.ui.Dialog({
		title: __('Choose Strategy'),
		fields: [
			{
				label: __('Strategy'),
				fieldname: 'strategy',
				fieldtype: 'Select',
				options: ['FIFO', 'LIFO', 'Deplete maximum number of Bins', 'Deplete minimum number of Bins', 'Shortest Path'],
				reqd: 1,
				default: 'Shortest Path',
			},
		],
		primary_action: async () => {
			let data = await d.get_values()
			frappe
				.xcall('inventory_tools.inventory_tools.overrides.pick_list.optimize_path', {
					doc: frm.doc.name,
					strategy: data.strategy,
				})
				.then(r => {
					d.hide()
				})
		},
		primary_action_label: __('Optimize Path'),
	})
	d.show()
}
