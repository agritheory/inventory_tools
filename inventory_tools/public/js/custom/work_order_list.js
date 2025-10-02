// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.listview_settings['Work Order'] = {
	refresh: listview => {
		listview.page.add_custom_menu_item(
			$('[data-view]').parent(),
			__('Alternative Workstations'),
			() => frappe.set_route('/alternative-workstation'),
			true,
			null,
			'branch'
		)
	},
}
