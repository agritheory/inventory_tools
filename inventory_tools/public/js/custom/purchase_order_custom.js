// Copyright (c) 2023, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Order', {
	onload_post_render: frm => {
		override_create_buttons(frm)
	},
	refresh: frm => {
		override_create_buttons(frm)
	},
})

function override_create_buttons(frm) {
	if (!frm.doc.multi_company_purchase_order || frm.doc.docstatus != 1) {
		return
	}

	let aggregated_purchasing_warehouse = undefined
	frappe.db.get_value('Buying Settings', 'Buying Settings', 'aggregated_purchasing_warehouse').then(r => {
		aggregated_purchasing_warehouse = r.message.aggregated_purchasing_warehouse
		if (!aggregated_purchasing_warehouse) {
			frm.remove_custom_button('Purchase Invoice', 'Create')
			frm.remove_custom_button('Purchase Receipt', 'Create')
			frm.remove_custom_button('Payment', 'Create')
			frm.remove_custom_button('Payment Request', 'Create')
			frm.remove_custom_button('Subscription', 'Create')
			frm.add_custom_button(
				'Create Purchase Invoices',
				async () => {
					await create_pis(frm)
				},
				'Create'
			)
			frm.add_custom_button(
				'Create Purchase Receipts',
				async () => {
					await create_prs(frm)
				},
				'Create'
			)
		} else {
			frm.add_custom_button(
				'Intercompany Sale and Transfer',
				async () => {
					await create_sis(frm)
				},
				'Create'
			)
		}
	})
}

async function create_pis(frm) {
	await create_dialog(
		frm,
		__('Create New Purchase Invoices'),
		__('Select Items and Locations to Invoice'),
		'inventory_tools.inventory_tools.overrides.purchase_order.make_purchase_invoices',
		__('Create Purchase Invoices')
	)
}

async function create_prs(frm) {
	await create_dialog(
		frm,
		__('Create New Purchase Receipts'),
		__('Select Items and Locations to Receive'),
		'inventory_tools.inventory_tools.overrides.purchase_order.make_purchase_receipts',
		__('Create Purchase Receipts')
	)
}

async function create_sis(frm) {
	await create_dialog(
		frm,
		__('Create Intercompany Sale and Transfer'),
		__('Select Items and Locations to Transfer'),
		'inventory_tools.inventory_tools.overrides.purchase_order.make_sales_invoices',
		__('Create Intercompany Sales Invoice')
	)
}

async function create_dialog(frm, title, label, method, primary_action_label) {
	let items_data = frm.doc.items.filter(r => {
		return r.company != frm.doc.company && r.rate != 0.0 && r.stock_qty > 0.0
	})
	return new Promise(resolve => {
		let table_fields = {
			fieldname: 'locations',
			fieldtype: 'Table',
			label: label,
			editable_grid: 0,
			read_only: 1,
			fields: [
				{
					fieldtype: 'Data',
					fieldname: 'company',
					label: __('Company'),
					read_only: 1,
					in_list_view: 1,
				},
				{
					fieldtype: 'Data',
					read_only: 1,
					fieldname: 'warehouse',
					label: __('Warehouse'),
					in_list_view: 1,
				},
				{
					fieldtype: 'Data',
					fieldname: 'item_code',
					label: __('Item'),
					read_only: 1,
					in_list_view: 1,
				},
				{
					fieldtype: 'Float',
					fieldname: 'qty',
					label: __('Quantity'),
					read_only: 1,
					in_list_view: 1,
				},
				{
					fieldtype: 'Data',
					fieldname: 'material_request_item',
					label: __('Material Request Item'),
					hidden: 1,
				},
			],
			data: items_data,
			get_data: () => {
				return items_data
			},
		}
		let dialog = new frappe.ui.Dialog({
			title: title,
			fields: [table_fields],
			size: 'extra-large',
			primary_action: () => {
				let rows = dialog.fields_dict.locations.grid.get_selected()
				frappe.xcall(method, { docname: frm.doc.name, rows: rows }).then(r => {
					resolve(dialog.hide())
				})
			},
			primary_action_label: primary_action_label,
		})
		dialog.show()
		dialog.wrapper.find('.grid-buttons').hide()
		// dialog.get_close_btn()
	})
}
