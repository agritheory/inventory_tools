// Copyright (c) 2023, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inventory Tools Settings', {
	onload(frm) {
		set_filters(frm)
		toggle_pack_stock_reservation_fields(frm)
	},
	refresh(frm) {
		set_filters(frm)
		toggle_pack_stock_reservation_fields(frm)
	},
	enable_alternative_sales_workflow(frm) {
		toggle_pack_stock_reservation_fields(frm)
	},
})

function toggle_pack_stock_reservation_fields(frm) {
	const reserveFields = ['reserve_stock_on_packing_slip', 'reserve_stock_on_shipment', 'column_break_pack_reserve']
	const showWhenAltWorkflow = frm.doc.enable_alternative_sales_workflow

	frappe.db.get_single_value('Stock Settings', 'enable_stock_reservation').then(enabled => {
		const show = showWhenAltWorkflow && cint(enabled)
		reserveFields.forEach(fieldname => {
			frm.toggle_display(fieldname, show)
		})
	})
}

function set_filters(frm) {
	frm.set_query('cartonization_doctypes', () => {
		const allowed_doctypes = ['Pick List', 'Stock Entry', 'Delivery Note', 'Packing Slip']
		return {
			filters: {
				name: ['in', allowed_doctypes],
			},
		}
	})
	frm.set_query('default_quarantine_warehouse', () => {
		return {
			filters: {
				company: frm.doc.company,
			},
		}
	})
	frm.set_query('aggregated_purchasing_warehouse', () => {
		return {
			filters: {
				company: frm.doc.purchase_order_aggregation_company,
				is_group: 0,
			},
		}
	})
}
