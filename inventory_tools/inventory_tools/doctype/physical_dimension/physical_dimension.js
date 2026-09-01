// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Physical Dimension', {
	refresh(frm) {
		frm.set_query('reference_doctype', () => ({
			filters: {
				name: ['in', ['Item', 'Vehicle', 'Warehouse', 'Workstation']],
			},
		}))

		if (frm.fields_dict.item_uom) {
			frm.set_query('item_uom', () => ({
				query:
					'inventory_tools.inventory_tools.doctype.physical_dimension.physical_dimension.physical_dimension_item_uom_query',
				filters: { item_code: frm.doc.reference_document },
			}))
		}
	},
	reference_doctype(frm) {
		if (frm.doc.reference_doctype !== 'Item') {
			frm.set_value('item_uom', '')
			return
		}
		fill_item_uom_from_stock_uom(frm)
	},
	reference_document(frm) {
		if (frm.doc.reference_doctype !== 'Item' || !frm.doc.reference_document) {
			return
		}
		frm.set_value('item_uom', '')
		fill_item_uom_from_stock_uom(frm)
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

function fill_item_uom_from_stock_uom(frm) {
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
