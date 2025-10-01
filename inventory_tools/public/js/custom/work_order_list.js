// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.listview_settings['Work Order'] = {
	refresh(listview) {
		// Add button in the menu
		listview.page.add_menu_item(__('Alternative Workstations'), () => {
			frappe.set_route('workstation-selection')
		})
	},
}
