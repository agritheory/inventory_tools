// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Packing Slip', {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.delivery_note) {
			return
		}

		frappe.db.get_value('Delivery Note', frm.doc.delivery_note, ['docstatus', 'company']).then(r => {
			if (!r.message || r.message.docstatus !== 0) {
				return
			}
			if (!inventory_tools.outbound_shipping.is_enabled(r.message.company)) {
				return
			}

			frm.add_custom_button(__('Delivery Note'), () => {
				frappe.confirm(__('Submit the linked draft Delivery Note?'), () => {
					frappe.call({
						method:
							'inventory_tools.inventory_tools.overrides.outbound_shipping.submit_delivery_note_from_packing_slip_whitelisted',
						args: { packing_slip_name: frm.doc.name },
						freeze: true,
						callback(res) {
							if (res.message) {
								inventory_tools.outbound_shipping.route_to('Delivery Note', res.message)
							}
						},
					})
				})
			})
		})
	},
})
