// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

frappe.provide('inventory_tools.alternative_sales_workflow')

inventory_tools.alternative_sales_workflow.is_enabled = function (company) {
	if (!company || !frappe.boot.inventory_tools_settings) {
		return false
	}
	const settings = frappe.boot.inventory_tools_settings[company]
	return settings && settings.enable_alternative_sales_workflow
}

inventory_tools.alternative_sales_workflow.route_to = function (doctype, name) {
	frappe.set_route('Form', doctype, name)
}

inventory_tools.alternative_sales_workflow.open_mapped_doc = function (method, frm, args) {
	return frappe.model.open_mapped_doc({
		method,
		frm,
		args,
		freeze: true,
	})
}

inventory_tools.alternative_sales_workflow.call_and_route = function (method, args) {
	return frappe.call({ method, args, freeze: true }).then(r => {
		if (r.message) {
			let doctype = 'Delivery Note'
			if (method.includes('submit_delivery_note') || method.includes('make_delivery_note')) {
				doctype = 'Delivery Note'
			} else if (method.includes('packing_slip')) {
				doctype = 'Packing Slip'
			} else if (method.includes('shipment')) {
				doctype = 'Shipment'
			}
			inventory_tools.alternative_sales_workflow.route_to(doctype, r.message)
		}
	})
}
