// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Entry', {
	on_submit: frm => {
		if (frm.doc.docstatus === 1) {
			frappe
				.call(
					'inventory_tools.inventory_tools.overrides.stock_entry.get_production_item_if_work_orders_for_required_item_exists',
					{ stock_entry_name: frm.doc.name }
				)
				.then(r => {
					if (r.message) {
						frappe.msgprint({
							title: __(`There are open work orders that ${r.message} is in the BOM`),
							message: __(`Do you want to view the work orders that use "${r.message}"?`),
							primary_action_label: __('Yes'),
							primary_action: {
								action(values) {
									frappe.set_route('list', 'Work Order', {
										'Work Order Item.item_code': r.message,
										status: 'Not Started',
									})
								},
							},
						})
					}
				})
		}
	},
})
