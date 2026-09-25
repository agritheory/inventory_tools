// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('BOM', {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus < 2) {
			frm.remove_custom_button(__('Update Cost'))
			frm.add_custom_button(__('Update Cost'), function () {
				let dialog = new frappe.ui.Dialog({
					title: __('Update Cost'),
					fields: [
						{
							fieldname: 'as_of_date',
							fieldtype: 'Date',
							label: __('As of Date'),
							default: frappe.datetime.get_today(),
							reqd: 1,
							description: __(
								'Operating costs from the Workstation Operating Cost table will be applied based on this date.'
							),
						},
					],
					primary_action_label: __('Update'),
					primary_action(values) {
						dialog.hide()
						frappe.call({
							doc: frm.doc,
							method: 'update_cost',
							freeze: true,
							args: {
								update_parent: true,
								save: true,
								from_child_bom: false,
								as_of_date: values.as_of_date,
							},
							callback(r) {
								refresh_field('items')
								if (!r.exc) frm.refresh_fields()
							},
						})
					},
				})
				dialog.show()
			})
		}
	},
})
