// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Order', {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus !== 1) {
			return
		}
		if (!inventory_tools.outbound_shipping.is_enabled(frm.doc.company)) {
			return
		}
		if (['Closed', 'Completed'].includes(frm.doc.status)) {
			return
		}

		frm.add_custom_button(
			__('Packing Slip'),
			() =>
				inventory_tools.outbound_shipping.call_and_route(
					'inventory_tools.inventory_tools.overrides.outbound_shipping.make_packing_slip_from_sales_order_whitelisted',
					{ sales_order_name: frm.doc.name }
				),
			__('Create')
		)

		frm.add_custom_button(
			__('Shipment'),
			() =>
				inventory_tools.outbound_shipping.call_and_route(
					'inventory_tools.inventory_tools.overrides.outbound_shipping.make_shipment_from_sales_order_whitelisted',
					{ sales_order_name: frm.doc.name }
				),
			__('Create')
		)
	},
})
