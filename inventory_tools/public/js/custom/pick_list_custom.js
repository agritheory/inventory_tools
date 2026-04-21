// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

const STRATEGY_OPTIONS = ['FIFO', 'LIFO', 'Deplete maximum number of Bins', 'Deplete minimum number of Bins']

frappe.ui.form.on('Pick List', {
	onload: frm => {
		const setting = frm.doc.__onload && frm.doc.__onload.default_route_optimization_strategy
		frm._default_route_strategy = setting && setting !== 'Use Source Document Order' ? setting : STRATEGY_OPTIONS[0]
	},
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
				options: STRATEGY_OPTIONS,
				reqd: 1,
				default: frm._default_route_strategy || STRATEGY_OPTIONS[0],
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
					frm.clear_table('locations')
					r.forEach(item => {
						frm.add_child('locations', item)
					})
					frm.refresh_field('locations')
					d.hide()
				})
		},
		primary_action_label: __('Optimize Path'),
	})
	d.show()
}
