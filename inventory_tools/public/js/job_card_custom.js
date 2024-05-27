frappe.ui.form.on('Job Card', {
	refresh: frm => {
		if (frm.doc.operation) {
			set_workstation_query(frm)
			set_work_order_query(frm)
		}
		add_switch_work_order_action(frm)
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

function set_work_order_query(frm) {
	if (frm.is_new()) {
		return
	}
	frm.set_query('work_order', doc => {
		return {
			filters: {
				production_item: doc.production_item,
			},
		}
	})
}

function add_switch_work_order_action(frm) {
	if (frm.doc.docstatus != 1) {
		return
	}
	frappe.db.get_value('Inventory Tools Settings', { company: frm.doc.company }, 'allow_switch_work_order').then(r => {
		if (r && r.message && r.message.allow_switch_work_order) {
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
											['status', '!=', 'Closed'],
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
	})
}
