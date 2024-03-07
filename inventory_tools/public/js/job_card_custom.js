frappe.ui.form.on('Job Card', {
	refresh: frm => {
		if (frm.doc.operation) {
			set_workstation_query(frm)
		}
		if (frm.doc.docstatus == 1) {
			add_swith_work_order_action(frm)
		}
	},
	operation: frm => {
		set_workstation_query(frm)
	},
})

function set_workstation_query(frm) {
	frm.set_query('workstation', doc => {
		return {
			query: 'inventory_tools.inventory_tools.overrides.workstation.get_alternative_workstations',
			filters: {
				operation: doc.operation,
			},
		}
	})
}

function add_swith_work_order_action(frm) {
	frm.add_custom_button(
		__('Switch Work Order'),
		function () {
			let dialog = new frappe.ui.Dialog({
				title: __('Select a Work Order'),
				fields: [
					{
						label: __('Work Order'),
						fieldname: 'work_order',
						fieldtype: 'Link',
						options: 'Work Order',
						reqd: 1,
						get_query: function () {
							return {
								filters: [
									['docstatus', '=', '1'],
									['bom_no', '=', frm.doc.bom_no],
									['company', '=', frm.doc.company],
									['name', '!=', frm.doc.work_order],
								],
							}
						},
					},
				],
				primary_action: () => {
					var args = dialog.get_values()
					frappe
						.xcall('inventory_tools.inventory_tools.overrides.job_card.switch_job_card_work_order', {
							job_card: frm.doc.name,
							work_order: args.work_order,
						})
						.then(r => {
							frm.reload_doc()
							frappe.msgprint(__('Work Order Switched.'))
							dialog.hide()
						})
				},
				primary_action_label: __('Switch Work Order'),
			})
			dialog.show()
		},
		__('Make')
	)
}
