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

inventory_tools.alternative_sales_workflow.get_pack_reserve_mode = function (company, pack_doctype) {
	if (!company || !frappe.boot.inventory_tools_settings) {
		return 'Never'
	}
	const settings = frappe.boot.inventory_tools_settings[company]
	if (!settings || !settings.enable_alternative_sales_workflow) {
		return 'Never'
	}
	if (pack_doctype === 'Packing Slip') {
		return settings.reserve_stock_on_packing_slip || 'Always'
	}
	return settings.reserve_stock_on_shipment || 'Ask'
}

inventory_tools.alternative_sales_workflow.setup_pack_stock_reservation = function (frm, pack_doctype) {
	const company_resolver = pack_doctype === 'Packing Slip' ? resolve_packing_slip_company : resolve_shipment_company

	company_resolver(frm).then(company => {
		if (!inventory_tools.alternative_sales_workflow.is_enabled(company)) {
			return
		}

		frappe.db.get_single_value('Stock Settings', 'enable_stock_reservation').then(enabled => {
			if (!cint(enabled)) {
				return
			}

			setup_pack_stock_reservation_buttons(frm, pack_doctype)
		})
	})
}

inventory_tools.alternative_sales_workflow.confirm_pack_stock_reservation_on_submit = async function (
	frm,
	pack_doctype
) {
	if (frm.doc.docstatus !== 0) {
		return true
	}

	const company_resolver = pack_doctype === 'Packing Slip' ? resolve_packing_slip_company : resolve_shipment_company
	const company = await company_resolver(frm)
	if (!inventory_tools.alternative_sales_workflow.is_enabled(company)) {
		return true
	}

	const stockReservationEnabled = await frappe.db.get_single_value('Stock Settings', 'enable_stock_reservation')
	if (!cint(stockReservationEnabled)) {
		return true
	}

	if (inventory_tools.alternative_sales_workflow.get_pack_reserve_mode(company, pack_doctype) !== 'Ask') {
		return true
	}

	if (pack_doctype === 'Packing Slip') {
		if (frm.doc.delivery_note) {
			return true
		}
		const hasSoLines = (frm.doc.items || []).some(item => item.so_detail)
		if (!hasSoLines) {
			return true
		}
	} else {
		const hasSoLines = (frm.doc.shipment_delivery_note || []).some(row => row.so_detail)
		if (!hasSoLines) {
			return true
		}
	}

	const method =
		pack_doctype === 'Packing Slip'
			? 'inventory_tools.inventory_tools.overrides.pack_stock_reservation.packing_slip_needs_stock_reservation'
			: 'inventory_tools.inventory_tools.overrides.pack_stock_reservation.shipment_needs_stock_reservation'
	const argName = pack_doctype === 'Packing Slip' ? 'packing_slip_name' : 'shipment_name'

	const result = await frappe.call({
		method,
		args: { [argName]: frm.doc.name },
	})
	if (!result.message) {
		return true
	}

	return new Promise(resolve => {
		frappe.confirm(
			__('Reserve stock for the unreserved Sales Order lines on this document?'),
			() => {
				frm.doc.reserve_stock_on_submit = 1
				resolve(true)
			},
			() => resolve(true)
		)
	})
}

function setup_pack_stock_reservation_buttons(frm, pack_doctype) {
	if (frm.doc.docstatus !== 1) {
		return
	}

	if (frm.doc.__onload && frm.doc.__onload.has_unreserved_pack_stock) {
		const createMethod =
			pack_doctype === 'Packing Slip'
				? 'inventory_tools.inventory_tools.overrides.pack_stock_reservation.create_packing_slip_stock_reservation_entries'
				: 'inventory_tools.inventory_tools.overrides.pack_stock_reservation.create_shipment_stock_reservation_entries'
		const argName = pack_doctype === 'Packing Slip' ? 'packing_slip_name' : 'shipment_name'

		frm.add_custom_button(
			__('Reserve'),
			() => {
				frappe.call({
					method: createMethod,
					args: { [argName]: frm.doc.name },
					freeze: true,
					freeze_message: __('Reserving Stock...'),
					callback: () => frm.reload_doc(),
				})
			},
			__('Stock Reservation')
		)
	}

	if (frm.doc.__onload && frm.doc.__onload.has_pack_reserved_stock) {
		const cancelMethod =
			pack_doctype === 'Packing Slip'
				? 'inventory_tools.inventory_tools.overrides.pack_stock_reservation.cancel_packing_slip_stock_reservation_entries'
				: 'inventory_tools.inventory_tools.overrides.pack_stock_reservation.cancel_shipment_stock_reservation_entries'
		const argName = pack_doctype === 'Packing Slip' ? 'packing_slip_name' : 'shipment_name'

		frm.add_custom_button(
			__('Unreserve'),
			() => {
				frappe.confirm(__('The reserved stock will be released. Are you certain you wish to proceed?'), () => {
					frappe.call({
						method: cancelMethod,
						args: { [argName]: frm.doc.name },
						freeze: true,
						freeze_message: __('Unreserving Stock...'),
						callback: () => frm.reload_doc(),
					})
				})
			},
			__('Stock Reservation')
		)
	}
}

async function resolve_packing_slip_company(frm) {
	if (frm.doc.delivery_note) {
		const result = await frappe.db.get_value('Delivery Note', frm.doc.delivery_note, 'company')
		return result.message?.company
	}

	const soName = (frm.doc.items || []).find(item => item.against_sales_order)?.against_sales_order
	if (!soName) {
		return null
	}

	const result = await frappe.db.get_value('Sales Order', soName, 'company')
	return result.message?.company
}

async function resolve_shipment_company(frm) {
	if (frm.doc.delivery_note) {
		const result = await frappe.db.get_value('Delivery Note', frm.doc.delivery_note, 'company')
		return result.message?.company
	}

	if (frm.doc.pickup_company) {
		return frm.doc.pickup_company
	}

	const soName = (frm.doc.shipment_delivery_note || []).find(row => row.against_sales_order)?.against_sales_order
	if (!soName) {
		return null
	}

	const result = await frappe.db.get_value('Sales Order', soName, 'company')
	return result.message?.company
}
