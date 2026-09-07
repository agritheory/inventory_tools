// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Order', {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus !== 1) {
			return
		}
		if (!inventory_tools.alternative_sales_workflow.is_enabled(frm.doc.company)) {
			return
		}
		if (['Closed', 'Completed'].includes(frm.doc.status)) {
			return
		}

		frm.add_custom_button(
			__('Packing Slip'),
			() =>
				inventory_tools.alternative_sales_workflow.open_mapped_doc(
					'inventory_tools.inventory_tools.overrides.alternative_sales_workflow.make_packing_slip_from_sales_order_whitelisted',
					frm,
					{ sales_order_name: frm.doc.name }
				),
			__('Create')
		)

		frm.add_custom_button(
			__('Shipment'),
			() =>
				inventory_tools.alternative_sales_workflow.open_mapped_doc(
					'inventory_tools.inventory_tools.overrides.alternative_sales_workflow.make_shipment_from_sales_order_whitelisted',
					frm,
					{ sales_order_name: frm.doc.name }
				),
			__('Create')
		)
	},
})
