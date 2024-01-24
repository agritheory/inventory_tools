frappe.ui.form.on('Stock Entry', {
	refresh: frm => {
		if (frm.doc.docstatus === 1) {
			frappe
				.call(
					'inventory_tools.inventory_tools.overrides.stock_entry.get_production_item_if_work_orders_for_required_item_exists',
					{ stock_entry_name: frm.doc.name }
				)
				.then(r => {
					if (r.message) {
						frappe.msgprint({
							title: __(`Open Work Orders requires ${r.message}`),
							message: __(`View Work Orders that requires ${r.message}?`),
							primary_action_label: __('Yes'),
							primary_action: {
								action(values) {
									frappe.set_route('list', 'Work Order', {
										'Work Order Item.item_code': 'Pie Crust',
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
