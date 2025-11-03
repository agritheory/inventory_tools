// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Plant Floor', {
	onload_post_render: frm => {
		inventory_tools.mount_plant_floor(frm)
	},
	refresh: frm => {
		frm.page.wrapper.find('.layout-side-section').hide()
	},
})
