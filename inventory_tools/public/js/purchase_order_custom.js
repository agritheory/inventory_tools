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
