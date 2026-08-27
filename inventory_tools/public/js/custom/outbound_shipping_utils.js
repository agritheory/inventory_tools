// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

frappe.provide('inventory_tools.outbound_shipping')

inventory_tools.outbound_shipping.is_enabled = function (company) {
	if (!company || !frappe.boot.inventory_tools_settings) {
		return false
	}
	const settings = frappe.boot.inventory_tools_settings[company]
	return settings && settings.enable_sales_order_outbound_shipping
}

inventory_tools.outbound_shipping.route_to = function (doctype, name) {
	frappe.set_route('Form', doctype, name)
}

inventory_tools.outbound_shipping.call_and_route = function (method, args) {
	return frappe.call({ method, args, freeze: true }).then(r => {
		if (r.message) {
			const doctype = method.includes('packing_slip')
				? 'Packing Slip'
				: method.includes('shipment')
				  ? 'Shipment'
				  : 'Delivery Note'
			inventory_tools.outbound_shipping.route_to(doctype, r.message)
		}
	})
}
