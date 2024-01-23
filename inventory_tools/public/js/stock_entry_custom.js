frappe.ui.form.on('Stock Entry', {
	refresh: frm => {
        if (frm.docstatus === 1) {
            frappe.call('inventory_tools.inventory_tools.overrides.stock_entry.get_production_item_if_work_orders_for_required_item_exists', {'stock_entry_name': frm.doc.name}).then(r => {
                if (r.message) {
                    let dialog = new frappe.ui.Dialog({
                        title: __(`View Work Orders that requires ${r.message}?`),
                        primary_action: () => {
                            frappe.set_route('list', 'Work Order', {'Work Order Item.item_code': r.message, 'status': 'Not Started'})
                        },
                        primary_action_label: __('Yes'),
                    })
                    dialog.show()
                }
            })
        }
	},
})
