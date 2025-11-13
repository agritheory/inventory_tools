// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Workstation', {
	refresh: frm => {
		// frm.set_query('')
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
