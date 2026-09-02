// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Packing Slip', {
	refresh(frm) {
		show_packing_slip_delivery_note_button(frm)
	},
})

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

async function show_packing_slip_delivery_note_button(frm) {
	if (frm.is_new() || frm.doc.docstatus !== 1) {
		return
	}

	const company = await resolve_packing_slip_company(frm)
	if (!inventory_tools.alternative_sales_workflow.is_enabled(company)) {
		return
	}

	const hasSoLines = (frm.doc.items || []).some(item => item.so_detail || item.against_sales_order)
	if (!frm.doc.delivery_note && !hasSoLines) {
		return
	}

	if (frm.doc.delivery_note) {
		const result = await frappe.db.get_value('Delivery Note', frm.doc.delivery_note, 'docstatus')
		if (!result.message || result.message.docstatus !== 0) {
			return
		}
	}

	frm.add_custom_button(__('Delivery Note'), () => {
		frappe.confirm(__('Create and submit the Delivery Note from this Packing Slip?'), () => {
			inventory_tools.alternative_sales_workflow.call_and_route(
				'inventory_tools.inventory_tools.overrides.alternative_sales_workflow.submit_delivery_note_from_packing_slip_whitelisted',
				{ packing_slip_name: frm.doc.name }
			)
		})
	})
}
