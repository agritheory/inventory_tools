// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Workstation', {
	refresh: frm => {
		set_item_query(frm)
		set_read_only(frm)
	},
})

frappe.ui.form.on('Workstation Working Hour', {
	shift_type: (frm, cdt, cdn) => {
		row = locals[cdt][cdn]
		if (!row.shift_type) {
			return
		}
		frappe.db.get_value('Shift Type', row.shift_type, ['start_time', 'end_time']).then(r => {
			frappe.model.set_value(row.doctype, row.name, 'start_time', r.message.start_time)
			frappe.model.set_value(row.doctype, row.name, 'end_time', r.message.end_time)
		})
	},
})

frappe.ui.form.on('Workstation Operating Cost', {
	item_code: (frm, cdt, cdn) => {
		row = locals[cdt][cdn]
		if (!row.item_code) {
			return
		}
		frappe
			.xcall(
				'inventory_tools.inventory_tools.doctype.workstation_operating_cost.workstation_operating_cost.fetch_default_expense_account',
				{ item_code: row.item_code, company: frm.doc.company }
			)
			.then(r => {
				frappe.model.set_value(row.doctype, row.name, 'account', r)
			})
	},
})

function set_item_query(frm) {
	frm.set_query('item_code', 'workstation_operating_cost', () => {
		return {
			filters: {
				is_stock_item: 0,
				is_fixed_asset: 0,
				disabled: 0,
			},
		}
	})
}

function set_read_only(frm) {
	if (frm.doc.workstation_operating_cost && frm.doc.workstation_operating_cost.length > 0) {
		frm.set_df_property('hour_rate_labour', 'read_only', 1)
		frm.set_df_property('hour_rate_electricity', 'read_only', 1)
		frm.set_df_property('hour_rate_consumable', 'read_only', 1)
		frm.set_df_property('hour_rate_rent', 'read_only', 1)
	} else {
		frm.set_df_property('hour_rate_labour', 'read_only', 0)
		frm.set_df_property('hour_rate_electricity', 'read_only', 0)
		frm.set_df_property('hour_rate_consumable', 'read_only', 0)
		frm.set_df_property('hour_rate_rent', 'read_only', 0)
	}
}
