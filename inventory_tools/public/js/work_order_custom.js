// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Order', {
	setup: frm => {
		frm.custom_make_buttons = {
			'New Subcontract PO': 'Create Subcontract PO',
			'Add to Existing PO': 'Add to Existing PO',
		}
	},
	refresh: frm => {
		manage_subcontracting_buttons(frm)
		get_workstations(frm)
	},
	operation: frm => {
		get_workstations(frm)
	},
})

function get_workstations(frm) {
	frm.set_query('workstation', 'operations', (doc, cdt, cdn) => {
		var d = locals[cdt][cdn]
		if (!d.operation) {
			frappe.throw('Please select a Operation first.')
		}
		return {
			query: 'inventory_tools.inventory_tools.overrides.workstation.get_alternative_workstations',
			filters: {
				operation: d.operation,
			},
		}
	})
}

function manage_subcontracting_buttons(frm) {
	if (frm.doc.company) {
		frappe.db.get_value('BOM', { name: frm.doc.bom_no }, 'is_subcontracted').then(r => {
			if (r && r.message && r.message.is_subcontracted) {
				frappe.db
					.get_value('Inventory Tools Settings', { company: frm.doc.company }, 'enable_work_order_subcontracting')
					.then(r => {
						if (r && r.message && r.message.enable_work_order_subcontracting && frm.doc.docstatus == 1) {
							frm.add_custom_button(
								__('Create Subcontract PO'),
								() => make_subcontracting_po(frm),
								__('Subcontracting')
							)
							frm.add_custom_button(__('Add to Existing PO'), () => add_to_existing_po(frm), __('Subcontracting'))
						}
					})
			}
		})
	}
}

function make_subcontracting_po(frm) {
	let d = new frappe.ui.Dialog({
		title: __('Select Supplier'),
		fields: [
			{
				label: __('Supplier'),
				fieldname: 'supplier',
				fieldtype: 'Link',
				options: 'Supplier',
				reqd: 1,
			},
		],
		primary_action: async () => {
			let data = await d.get_values()
			frappe
				.xcall('inventory_tools.inventory_tools.overrides.work_order.make_subcontracted_purchase_order', {
					wo_name: frm.doc.name,
					supplier: data.supplier,
				})
				.then(r => {
					d.hide()
				})
		},
		primary_action_label: __('Create PO'),
	})
	d.show()
}

function add_to_existing_po(frm) {
	let d = new frappe.ui.Dialog({
		title: __('Add to Purchase Order'),
		fields: [
			{
				label: __('Purchase Order'),
				fieldname: 'purchase_order',
				fieldtype: 'Link',
				options: 'Purchase Order',
				reqd: 1,
			},
		],
		primary_action: function () {
			let data = d.get_values()
			frappe
				.xcall('inventory_tools.inventory_tools.overrides.work_order.add_to_existing_purchase_order', {
					wo_name: frm.doc.name,
					po_name: data.purchase_order,
				})
				.then(r => {
					d.hide()
				})
		},
		primary_action_label: __('Add to PO'),
	})
	d.show()
	d.fields_dict.purchase_order.get_query = () => {
		return {
			filters: {
				is_subcontracted: 1,
				docstatus: ['!=', 2],
				// TODO: can date filters in dialog be used to filter purchase orders?
			},
		}
	}
}
