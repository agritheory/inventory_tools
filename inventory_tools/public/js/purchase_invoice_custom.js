frappe.ui.form.on('Purchase Invoice', {
	refresh: function (frm) {
		show_subcontracting_fields(frm)
		frm.remove_custom_button(__('Fetch Stock Entries'))
		fetch_stock_entry_dialog(frm)
	},

	is_subcontracted: function (frm) {
		if (frm.doc.is_subcontracted) {
			show_subcontracting_fields(frm)
		}
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
				unhide_field('subcontracting')
			} else {
				hide_field('subcontracting')
			}
		})
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
	frm.get_field('subcontracting').grid.add_custom_button('Fetch Stock Entries', () => {
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
							console.log(r)
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
}
