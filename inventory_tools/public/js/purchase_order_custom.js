frappe.ui.form.on('Purchase Order', {
	refresh: function (frm) {
		show_subcontracting_fields(frm)
	},

	is_subcontracted: function (frm) {
		if (frm.doc.is_subcontracted) {
			show_subcontracting_fields(frm)
		}
	},
})

// TODO: override when a qty changes in item table, it changes the fg_item_qty (assumes same UOM)
// TODO: subcontracting table: autofill fields when a row is manually added and user selects the WO
// TODO: when subcontracting table row removed, adjust Item row fg_item_qty
// TODO: filter supplier warehouse to non-group

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
