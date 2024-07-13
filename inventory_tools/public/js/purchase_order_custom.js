// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Order', {
	refresh: frm => {
		show_subcontracting_fields(frm)
		setup_item_queries(frm)
		fetch_supplier_warehouse(frm)
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
	frappe.db
		.get_value('Inventory Tools Settings', { company: frm.doc.company }, 'enable_work_order_subcontracting')
		.then(r => {
			if (r && r.message && r.message.enable_work_order_subcontracting) {
				unhide_field('subcontracting')
				setTimeout(() => {
					frm.remove_custom_button('Purchase Receipt', 'Create')
					frm.remove_custom_button('Subcontracting Order', 'Create')
				}, 1000)
			} else {
				hide_field('subcontracting')
			}
		})
}

function setup_item_queries(frm) {
	frm.set_query('item_code', 'items', () => {
		if (me.frm.doc.is_subcontracted) {
			var filters = { supplier: me.frm.doc.supplier }
			if (me.frm.doc.is_old_subcontracting_flow) {
				filters['is_sub_contracted_item'] = 1
			} else {
				frappe.db.get_value('Inventory Tools Settings', frm.doc.company, 'enable_work_order_subcontracting').then(r => {
					if (!r.message.enable_work_order_subcontracting) {
						filters['is_stock_item'] = 0
					}
				})
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
