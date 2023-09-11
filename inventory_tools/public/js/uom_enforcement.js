// Copyright(c) 2023, AgriTheory and contributors
// For license information, please see license.txt

frappe.provide('frappe.ui.form')

$(document).on('page-change', () => {
	page_changed()
})

function page_changed() {
	frappe.after_ajax(() => {
		const route = frappe.get_route()
		frappe.call('inventory_tools.inventory_tools.overrides.uom.get_uom_enforcement').then(r => {
			frappe.uom_enforcement = r.message
			if (route[0] == 'Form' && Object.keys(frappe.uom_enforcement).includes(route[1])) {
				frappe.ui.form.on(route[1], {
					onload_post_render: frm => {
						// onload runs too soon
						setup_uom_enforcement(frm)
					},
				})
				frappe.ui.form.on(route[1], {
					refresh: frm => {
						setup_uom_enforcement(frm)
					},
				})
			}
		})
	})
}

function setup_uom_enforcement(frm) {
	for (const [form_doctype, config] of Object.entries(frappe.uom_enforcement[frm.doc.doctype])) {
		// form setup
		if (frm.doc.doctype == form_doctype) {
			config.forEach(field => {
				frm.set_query(field, (_frm, cdt, cdn) => {
					let item_code_field = 'item_code'
					if (frm.doc.doctype == 'BOM') {
						item_code_field = 'item'
					} else if (frm.doc.doctype == 'Job Card') {
						item_code_field = 'production_item'
					}
					if (!frm.doc[item_code_field]) {
						return {}
					}
					return {
						query: 'inventory_tools.inventory_tools.overrides.uom.uom_restricted_query',
						filters: { parent: frm.doc.item_code },
					}
				})
			})
		} else {
			// child table setup
			for (const [table_field, fields] of Object.entries(config)) {
				fields.forEach(field => {
					frm.set_query(field, table_field, (_frm, cdt, cdn) => {
						if (!locals[cdt][cdn].item_code) {
							return {}
						}
						return {
							query: 'inventory_tools.inventory_tools.overrides.uom.uom_restricted_query',
							filters: { parent: locals[cdt][cdn].item_code },
						}
					})
				})
			}
		}
	}
}
