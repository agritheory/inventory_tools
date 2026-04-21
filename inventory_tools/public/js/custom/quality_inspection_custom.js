// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Inspection', {
	refresh: frm => {
		if (frm.doc.docstatus !== 1 || frm.doc.status !== 'Accepted') {
			return
		}
		frappe.db.get_value('Inventory Tools Settings', frm.doc.company || '', 'enable_quarantine_workflow').then(r => {
			if (!r || !r.message || !r.message.enable_quarantine_workflow) {
				return
			}
			frm.add_custom_button(__('Release from Quarantine'), () => {
				frappe
					.xcall('inventory_tools.inventory_tools.overrides.stock_entry.make_quarantine_release_stock_entry', {
						quality_inspection_name: frm.doc.name,
					})
					.then(se_name => {
						frappe.set_route('Form', 'Stock Entry', se_name)
					})
			})
		})
	},
})
