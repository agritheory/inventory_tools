// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Physical Dimension', {
	refresh(frm) {
		frm.set_query('reference_doctype', () => ({
			filters: {
				name: ['in', ['Item', 'Vehicle', 'Warehouse', 'Workstation']],
			},
		}))
	},
	reference_doctype(frm) {
		if (frm.doc.reference_doctype !== 'Item') {
			frm.set_value('item_uom', '')
		}
		set_item_uom_read_only_for_item_reference(frm)
		set_item_uom_from_item_stock_uom(frm)
	},
	reference_document(frm) {
		set_item_uom_read_only_for_item_reference(frm)
		set_item_uom_from_item_stock_uom(frm)
	},
	item_height(frm) {
		frm.trigger('calculate_item_volume')
	},
	item_length(frm) {
		frm.trigger('calculate_item_volume')
	},
	item_width(frm) {
		frm.trigger('calculate_item_volume')
	},
	calculate_item_volume(frm) {
		frm.set_value('item_volume', frm.doc.item_length * frm.doc.item_width * frm.doc.item_height)
	},
})

function set_item_uom_read_only_for_item_reference(frm) {
	const locked = frm.doc.reference_doctype === 'Item'
	frm.set_df_property('item_uom', 'read_only', locked ? 1 : 0)
}

function set_item_uom_from_item_stock_uom(frm) {
	if (frm.doc.reference_doctype !== 'Item' || !frm.doc.reference_document || frm.doc.item_uom) {
		return
	}
	return frappe.db.get_value('Item', frm.doc.reference_document, 'stock_uom').then(r => {
		const stock_uom = r?.message?.stock_uom
		if (stock_uom) {
			return frm.set_value('item_uom', stock_uom)
		}
	})
}
