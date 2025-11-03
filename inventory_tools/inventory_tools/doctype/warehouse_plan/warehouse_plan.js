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
		// set the walkable matrix directly into the plan
		const walkable_matrix = inventory_tools.$warehouse_plan.getWalkableString()
		frm.set_value('matrix', walkable_matrix)

		// set the drawn details for each warehouse
		const warehouses = inventory_tools.$warehouse_plan.getWarehouseArray()
		frm.call('set_warehouse_plan_details', { warehouses })
	},
})
