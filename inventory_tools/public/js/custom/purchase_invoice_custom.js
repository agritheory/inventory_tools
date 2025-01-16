frappe.ui.form.on('Purchase Invoice', {
	refresh: function (frm) {
		show_subcontracting_fields(frm)
		frm.remove_custom_button(__('Fetch Stock Entries'))
		fetch_stock_entry_dialog(frm)
		setup_item_queries(frm)
		fetch_supplier_warehouse(frm)
	},
	is_subcontracted: function (frm) {
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
		hide_field('update_stock')
		setTimeout(() => {
			frm.remove_custom_button('Purchase Receipt', 'Create')
		}, 1000)
	} else {
		hide_field('subcontracting')
		unhide_field('update_stock')
	}
	toggle_subcontracting_columns(frm)
}

function add_stock_entry_row(frm, row) {
	frm.add_child('subcontracting', {
		work_order: row.work_order,
		stock_entry: row.stock_entry,
		purchase_order: row.purchase_order,
		se_detail_name: row.se_detail_name,
		item_code: row.item_code,
		item_name: row.item_name,
		qty: row.qty,
		transfer_qty: row.transfer_qty,
		uom: row.uom,
		stock_uom: row.stock_uom,
		conversion_factor: row.conversion_factor,
		valuation_rate: row.valuation_rate,
		paid_qty: row.paid_qty,
		to_pay_qty: row.qty - row.paid_qty,
	})
	frm.refresh_field('subcontracting')
}

function fetch_stock_entry_dialog(frm) {
	if (!frm.is_new() && frm.doc.docstatus > 0) {
		return
	}
	let fetch_button = frm.get_field('subcontracting').grid.add_custom_button('Fetch Stock Entries', () => {
		let d = new frappe.ui.Dialog({
			title: __('Fetch Stock Entries'),
			fields: [
				{
					label: __('From'),
					fieldname: 'from_date',
					fieldtype: 'Date',
				},
				{
					fieldtype: 'Column Break',
					fieldname: 'col_break_1',
				},
				{
					label: __('To'),
					fieldname: 'to_date',
					fieldtype: 'Date',
				},
			],
			primary_action: function () {
				let data = d.get_values()
				let po = []
				frm.get_field('items').grid.grid_rows.forEach(item => {
					po.push(item.doc.purchase_order)
				})
				frappe
					.xcall('inventory_tools.inventory_tools.overrides.purchase_invoice.get_stock_entries', {
						purchase_orders: po,
						from_date: data.from_date,
						to_date: data.to_date,
					})
					.then(r => {
						if (r.length > 0) {
							frm.clear_table('subcontracting')
							r.forEach(d => {
								add_stock_entry_row(frm, d)
							})
						} else {
							frappe.msgprint(__('No Stock Entries found with the selected filters.'))
						}
						d.hide()
					})
			},
			primary_action_label: __('Get Stock Entries'),
		})
		d.show()
	})
	$(fetch_button).removeClass('btn-secondary').addClass('btn-primary')
}

function toggle_subcontracting_columns(frm) {
	if (!frm.doc.is_subcontracted) {
		// hide columns
		frm.get_field('subcontracting').grid.reset_grid()
		frm.get_field('subcontracting').grid.visible_columns.forEach((column, index) => {
			if (index >= frm.get_field('subcontracting').grid.visible_columns.length - 2) {
				column[0].columns = 1
				column[1] = 1
			}
		})
		for (let row of frm.get_field('subcontracting').grid.grid_rows) {
			if (row.open_form_button) {
				row.open_form_button.parent().remove()
				delete row.open_form_button
			}

			for (let field in row.columns) {
				if (row.columns[field] !== undefined) {
					row.columns[field].remove()
				}
			}
			delete row.columns
			row.columns = []
			row.render_row()
		}
	} else {
		// show subcontracting fields
		frm.get_field('items').grid.reset_grid()
		let user_defined_columns = frm.get_field('subcontracting').grid.visible_columns.map(col => {
			return col[0]
		})
		user_defined_columns.forEach((column, index) => {
			if (index > 2) {
				// leave first two columns alone
				column.columns = 1
			}
		})
		let paid_qty = frappe.meta.get_docfield(frm.get_field('subcontracting').grid.doctype, 'paid_qty')
		paid_qty.in_list_view = 1
		user_defined_columns.push(paid_qty)
		let to_pay_qty = frappe.meta.get_docfield(frm.get_field('subcontracting').grid.doctype, 'to_pay_qty')
		to_pay_qty.in_list_view = 1
		user_defined_columns.push(to_pay_qty)
		frm.get_field('subcontracting').grid.visible_columns = user_defined_columns.map(col => {
			return [col, col.columns]
		})
		for (let row of frm.get_field('subcontracting').grid.grid_rows) {
			if (row.open_form_button) {
				row.open_form_button.parent().remove()
				delete row.open_form_button
			}

			for (let field in row.columns) {
				if (row.columns[field] !== undefined) {
					row.columns[field].remove()
				}
			}
			delete row.columns
			row.columns = []
			row.render_row()
		}
	}
	frm.get_field('subcontracting').refresh()
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

function setup_supplier_warehouse_query(frm) {
	frm.set_query('supplier_warehouse', () => {
		return {
			filters: { is_group: 0 },
		}
	})
}
