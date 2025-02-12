// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.provide('inventory_tools')

frappe.ui.form.on('Warehouse Plan', {
	onload_post_render: frm => {
		inventory_tools.mount_warehouse_plan(frm)
	},
	refresh: frm => {
		frm.page.wrapper.find('.layout-side-section').hide()
	},
	validate: frm => {
		const matrix = inventory_tools.$warehouse_plan.getMatrixString()
		frm.set_value('matrix', matrix)
	},
})
