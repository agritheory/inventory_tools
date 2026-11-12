// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Card', {
	refresh: frm => {
		if (frm.doc.operation) {
			set_workstation_query(frm)
		}
		alternative_workstation_button(frm)
	},
	operation: frm => {
		set_workstation_query(frm)
	},
})

function set_workstation_query(frm) {
	frm.set_query('workstation', doc => {
		return {
			query: 'inventory_tools.inventory_tools.overrides.workstation.get_alternative_workstations',
			filters: {
				operation: frm.doc.operation,
				company: frm.doc.company,
				bom_no: frm.doc.bom_no,
			},
		}
	})
}

function alternative_workstation_button(frm) {
	if (frm.doc.docstatus != 1 || frm.doc.status === 'Completed' || !frm.doc.work_order || !frm.doc.company) {
		return
	}
	frappe.db
		.get_value('Inventory Tools Settings', { company: frm.doc.company }, [
			'allow_alternative_workstations',
			'allow_job_card_workstation_change',
		])
		.then(r => {
			const settings = r && r.message
			if (!settings) {
				return
			}
			if (settings.allow_alternative_workstations === 'Do Not Allow Alternative Workstations') {
				return
			}
			if (!settings.allow_job_card_workstation_change) {
				return
			}
			frm.add_custom_button(
				__('Alternative Workstations'),
				function () {
					inventory_tools.alternative_workstation.open(frm.doc.work_order)
				},
				__('View')
			)
		})
}
