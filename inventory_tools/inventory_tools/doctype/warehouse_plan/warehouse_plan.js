// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Warehouse Plan', {
	onload_post_render: frm => {
		inventory_tools.mount_warehouse_plan(frm)
	},
	refresh: frm => {
		frm.page.wrapper.find('.layout-side-section').hide()
	},
	validate: frm => {
		// not working
		const matrix = frm.warehouse_plan._instance.exposed.getMatrixString()
		console.log(matrix)
		// frm.set_value('matrix', matrix)
	},
})
