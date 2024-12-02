// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.listview_settings['Work Order'] = {
	refresh: listview => {
		listview.page.add_custom_menu_item(
			$('[data-view]').parent(),
			__('Optimizer'),
			() => frappe.set_route('/optimizer'),
			true,
			null,
			'gantt'
		)
	},
}
