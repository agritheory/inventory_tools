frappe.ui.form.on('Purchase Invoice', {
	refresh: function (frm) {
		show_subcontracting_fields(frm)
		frm.remove_custom_button(__('Fetch Stock Entries'))
		fetch_stock_entry_dialog(frm)
	},
})

function show_subcontracting_fields(frm) {
	if (!frm.doc.company || !frm.doc.is_subcontracted) {
		hide_field('subcontracting')
		return
	}
	frappe.db
		.get_value('Inventory Tools Settings', { company: frm.doc.company }, 'enable_work_order_subcontracting')
		.then(r => {
			if (r && r.message && r.message.enable_work_order_subcontracting) {
				// console.log('r.message:', r.message);
				return
			} else {
				hide_field('subcontracting')
			}
		})
}

function add_stock_entry_row(frm, row) {
	frm.add_child('subcontracting', {
		work_order: row.work_order,
		stock_entry: row.stock_entry,
		item_code: row.item_code,
		item_name: row.item_name,
		qty: row.qty,
		transfer_qty: row.transfer_qty,
		uom: row.uom,
		stock_uom: row.stock_uom,
		conversion_factor: row.conversion_factor,
		valuation_rate: row.valuation_rate,
	})
	frm.refresh_field('subcontracting')
}

function fetch_stock_entry_dialog(frm) {
	if (!frm.is_new() && frm.doc.docstatus > 0) {
		return
	}
	frm.get_field('subcontracting').grid.add_custom_button('Fetch Stock Entries', () => {
		let query_args = {}
		query_args.filters = {
			docstatus: 1,
			status: ['not in', ['Closed', , 'Not Started', 'Stopped']], // TODO: check applicable statuses for WO
			company: me.frm.doc.company,
		}

		let d = new frappe.ui.form.MultiSelectDialog({
			doctype: 'Work Order',
			target: me.frm,
			date_field: undefined,
			setters: {
				production_item: undefined,
			},
			get_query: () => query_args,
			add_filters_group: 1,
			allow_child_item_selection: undefined,
			child_fieldname: undefined,
			child_columns: undefined,
			size: undefined,
			action: function (selections, args) {
				let data = selections
				frappe
					.xcall('inventory_tools.overrides.purchase_invoice.get_stock_entries_by_work_order', {
						work_orders: data,
					})
					.then(r => {
						if (r.length > 0) {
							frm.clear_table('subcontracting')
							console.log(r)
							let aggregated_qty = {}
							r.forEach(d => {
								add_stock_entry_row(frm, d)
								if (aggregated_qty.hasOwnProperty(d.item_code)) {
									aggregated_qty[d.item_code] = aggregated_qty[d.item_code] + d.qty // TODO: use qty or transfer_qty?
								} else {
									aggregated_qty[d.item_code] = d.qty
								}
							})
							console.log('AGGREGATED QTYS BY ITEM:', aggregated_qty)
							// TODO: match aggregated total of received items to items table, update [new] field in table
						} else {
							frappe.msgprint(__('No Stock Entries found with the selected filters.'))
						}
						d.dialog.hide()
					})
			},
			primary_action_label: __('Get Stock Entries'),
		})
	})
}
