// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Entry', {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus !== 1 || frm.doc.purpose !== 'Material Transfer') {
			return
		}
		if (!frm.doc.pick_list) {
			return
		}
		if (!inventory_tools.outbound_shipping.is_enabled(frm.doc.company)) {
			return
		}

		const args = { stock_entry_name: frm.doc.name }

		frm.add_custom_button(
			__('Delivery Note'),
			() =>
				inventory_tools.outbound_shipping.call_and_route(
					'inventory_tools.inventory_tools.overrides.outbound_shipping.make_delivery_note_from_stock_entry_whitelisted',
					args
				),
			__('Create')
		)

		frm.add_custom_button(
			__('Packing Slip'),
			() =>
				inventory_tools.outbound_shipping.call_and_route(
					'inventory_tools.inventory_tools.overrides.outbound_shipping.make_packing_slip_from_stock_entry_whitelisted',
					args
				),
			__('Create')
		)

		frm.add_custom_button(
			__('Shipment'),
			() =>
				inventory_tools.outbound_shipping.call_and_route(
					'inventory_tools.inventory_tools.overrides.outbound_shipping.make_shipment_from_stock_entry_whitelisted',
					args
				),
			__('Create')
		)
	},
})
