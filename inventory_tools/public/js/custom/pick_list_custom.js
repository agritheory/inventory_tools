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
				options: ['FIFO', 'LIFO', 'Deplete maximum number of Bins', 'Deplete minimum number of Bins'],
				reqd: 1,
				default: 'Deplete maximum number of Bins',
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
					if (!Array.isArray(r)) {
						console.error('Invalid response format:', r)
						frappe.msgprint(__('Invalid response received from server.'))
						return
					}

					// Clear and repopulate the child table
					frm.clear_table('child_table_fieldname')
					r.forEach(item => {
						let child = frm.add_child('child_table_fieldname')
						child.item_code = item.item_code
						child.qty = item.qty
					})
					frm.refresh_field('child_table_fieldname')
				})
				.catch(error => {
					console.error('Error optimizing path:', error)
					frappe.msgprint({
						title: __('Error'),
						indicator: 'red',
						message: __('Failed to optimize path. Please try again.'),
					})
				})
				.finally(() => {
					setTimeout(() => {
						d.hide()
						frm.refresh()
					}, 200)
				})
		},
		primary_action_label: __('Optimize Path'),
	})
	d.show()
}
