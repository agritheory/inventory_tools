// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shipment', {
	refresh(frm) {
		if (frm.is_new()) {
			return
		}
		const company = frm.doc.pickup_company || frappe.defaults.get_default('company')
		if (!inventory_tools.outbound_shipping.is_enabled(company)) {
			return
		}

		const dn_names = [...new Set((frm.doc.shipment_delivery_note || []).map(r => r.delivery_note).filter(Boolean))]
		if (!dn_names.length) {
			return
		}

		frappe.db
			.get_list('Delivery Note', {
				filters: { name: ['in', dn_names], docstatus: 0 },
				fields: ['name'],
				limit: 1,
			})
			.then(rows => {
				if (!rows.length) {
					return
				}
				frm.add_custom_button(__('Delivery Note'), () => {
					frappe.confirm(__('Submit the linked draft Delivery Note?'), () => {
						frappe.call({
							method:
								'inventory_tools.inventory_tools.overrides.outbound_shipping.submit_delivery_note_from_shipment_whitelisted',
							args: { shipment_name: frm.doc.name },
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
