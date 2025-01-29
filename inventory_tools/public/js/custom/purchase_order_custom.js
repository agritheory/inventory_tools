frappe.ui.form.on('Purchase Order', {
	onload_post_render: frm => {
		override_create_buttons(frm)
	},
	refresh: frm => {
		show_subcontracting_fields(frm)
		setup_item_queries(frm)
		fetch_supplier_warehouse(frm)
		override_create_buttons(frm)
	},
	is_subcontracted: frm => {
		if (frm.doc.is_subcontracted) {
			show_subcontracting_fields(frm)
		}
	},
	company: frm => {
		setup_item_queries(frm)
		fetch_supplier_warehouse(frm)
	},
	supplier: frm => {
		fetch_supplier_warehouse(frm)
	},
})

// TODO: override when a qty changes in item table, it changes the fg_item_qty (assumes same UOM)
// TODO: subcontracting table: autofill fields when a row is manually added and user selects the WO
// TODO: when subcontracting table row removed, adjust Item row fg_item_qty

function show_subcontracting_fields(frm) {
	if (!frm.doc.company || !frm.doc.is_subcontracted) {
		hide_field('subcontracting')
		return
	}
	if (
		frappe.boot.inventory_tools_settings &&
		frappe.boot.inventory_tools_settings[frm.doc.company] &&
		frappe.boot.inventory_tools_settings[frm.doc.company].enable_work_order_subcontracting
	) {
		unhide_field('subcontracting')
		setTimeout(() => {
			frm.remove_custom_button('Purchase Receipt', 'Create')
			frm.remove_custom_button('Subcontracting Order', 'Create')
		}, 1000)
	} else {
		hide_field('subcontracting')
	}
}

function setup_item_queries(frm) {
	frm.set_query('item_code', 'items', () => {
		if (me.frm.doc.is_subcontracted) {
			var filters = { supplier: me.frm.doc.supplier }
			if (me.frm.doc.is_old_subcontracting_flow) {
				filters['is_sub_contracted_item'] = 1
			} else {
				if (
					frappe.boot.inventory_tools_settings &&
					frappe.boot.inventory_tools_settings[frm.doc.company] &&
					frappe.boot.inventory_tools_settings[frm.doc.company].enable_work_order_subcontracting
				) {
					filters['is_stock_item'] = 0
				}
			}
			return {
				query: 'erpnext.controllers.queries.item_query',
				filters: filters,
			}
		} else {
			return {
				query: 'erpnext.controllers.queries.item_query',
				filters: { supplier: me.frm.doc.supplier, is_purchase_item: 1, has_variants: 0 },
			}
		}
	})
}

function setup_supplier_warehouse_query(frm) {
	frm.set_query('supplier_warehouse', () => {
		return {
			filters: { is_group: 0 },
		}
	})
}

function fetch_supplier_warehouse(frm) {
	if (!frm.doc.company || !frm.doc.supplier) {
		return
	}
	frappe
		.xcall('inventory_tools.inventory_tools.overrides.purchase_invoice.fetch_supplier_warehouse', {
			company: frm.doc.company,
			supplier: frm.doc.supplier,
		})
		.then(r => {
			if (r && r.message) {
				frm.set_value('supplier_warehouse', r.message.supplier_warehouse)
			}
		})
}

function override_create_buttons(frm) {
	if (!frm.doc.multi_company_purchase_order || frm.doc.docstatus != 1) {
		return
	}
	let aggregated_purchasing_warehouse = undefined
	if (
		frm.doc.docstatus &&
		frappe.boot.inventory_tools_settings &&
		frappe.boot.inventory_tools_settings[frm.doc.company] &&
		frappe.boot.inventory_tools_settings[frm.doc.company].aggregated_purchasing_warehouse
	) {
		aggregated_purchasing_warehouse =
			frappe.boot.inventory_tools_settings[frm.doc.company].aggregated_purchasing_warehouse
	}
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
	let items_data = await get_items_data(frm)
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
			get_data: async () => {
				return await get_items_data(frm)
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

async function get_items_data(frm) {
	let items_data = []
	if (
		frm.doc.docstatus &&
		frappe.boot.inventory_tools_settings &&
		frappe.boot.inventory_tools_settings[frm.doc.company] &&
		frappe.boot.inventory_tools_settings[frm.doc.company].aggregated_purchasing_warehouse
	) {
		items_data = frm.doc.items
		items_data.forEach(row => {
			row.company = frm.doc.company
		})
		return items_data
	} else {
		let items_data = frm.doc.items.filter(r => {
			return r.company != frm.doc.company && r.rate != 0.0 && r.stock_qty > 0.0
		})
		let mrs = Array.from(
			new Set(
				frm.doc.items.map(r => {
					return r.material_request
				})
			)
		)
		await frappe.db
			.get_list('Material Request', { filters: { name: ['in', mrs] }, fields: ['name', 'company'] })
			.then(r => {
				console.log(r)
				r.forEach(mr => {
					items_data.forEach(row => {
						if (row.material_request == mr.name) {
							row.company = mr.company
						}
					})
				})
			})
		return items_data
	}
}
