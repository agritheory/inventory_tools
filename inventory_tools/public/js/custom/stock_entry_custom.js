// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Entry', {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus !== 1 || frm.doc.purpose !== 'Material Transfer') {
			return
		}
		if (!frm.doc.pick_list) {
			return
		}
		if (inventory_tools.alternative_sales_workflow.is_enabled(frm.doc.company)) {
			const args = { stock_entry_name: frm.doc.name }

			frm.add_custom_button(
				__('Delivery Note'),
				() =>
					inventory_tools.alternative_sales_workflow.call_and_route(
						'inventory_tools.inventory_tools.overrides.alternative_sales_workflow.make_delivery_note_from_stock_entry_whitelisted',
						args
					),
				__('Create')
			)

			frm.add_custom_button(
				__('Packing Slip'),
				() =>
					inventory_tools.alternative_sales_workflow.open_mapped_doc(
						'inventory_tools.inventory_tools.overrides.alternative_sales_workflow.make_packing_slip_from_stock_entry_whitelisted',
						frm,
						args
					),
				__('Create')
			)

			frm.add_custom_button(
				__('Shipment'),
				() =>
					inventory_tools.alternative_sales_workflow.open_mapped_doc(
						'inventory_tools.inventory_tools.overrides.alternative_sales_workflow.make_shipment_from_stock_entry_whitelisted',
						frm,
						args
					),
				__('Create')
			)
		}
	},
	on_submit: frm => {
		if (frm.doc.docstatus === 1) {
			frappe
				.call(
					'inventory_tools.inventory_tools.overrides.stock_entry.get_production_item_if_work_orders_for_required_item_exists',
					{ stock_entry_name: frm.doc.name }
				)
				.then(r => {
					if (r.message) {
						frappe.msgprint({
							title: __(`There are open work orders that ${r.message} is in the BOM`),
							message: __(`Do you want to view the work orders that use "${r.message}"?`),
							primary_action_label: __('Yes'),
							primary_action: {
								action(values) {
									frappe.set_route('list', 'Work Order', {
										'Work Order Item.item_code': r.message,
										status: 'Not Started',
									})
								},
							},
						})
					}
				})
		}
	},
})
