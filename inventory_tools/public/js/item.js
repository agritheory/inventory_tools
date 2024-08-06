frappe.ui.form.on('Item', {
	validate: frm => {
		if (frm.doc.weight_uom && frm.doc.weight_per_unit == 0) {
			frappe.throw(__("Please mention 'Weight Per Unit' along with Weight UOM."))
		}
	},
})
