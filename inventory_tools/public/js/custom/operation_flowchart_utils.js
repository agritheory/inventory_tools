// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

function render_operation_flowchart(frm) {
	if (inventory_tools.render_operation_flowchart) {
		inventory_tools.render_operation_flowchart(frm)
	}
}

function copy_operation_relation_defaults(frm, cdt, cdn) {
	const row = locals[cdt][cdn]
	if (!row.operation) {
		render_operation_flowchart(frm)
		return
	}
	frappe.db.get_value('Operation', row.operation, ['predecessor_relation', 'lag_mins']).then(r => {
		const defaults = r.message || {}
		frappe.model.set_value(cdt, cdn, {
			predecessor_relation: defaults.predecessor_relation || '',
			lag_mins: defaults.lag_mins || 0,
		})
	})
}

const parent_handlers = {
	refresh: render_operation_flowchart,
	routing: render_operation_flowchart,
	with_operations: render_operation_flowchart,
	bom_no: render_operation_flowchart,
	qty: render_operation_flowchart,
	planned_start_date: render_operation_flowchart,
	expected_delivery_date: render_operation_flowchart,
}

const operation_row_handlers = {
	operations_add: render_operation_flowchart,
	operations_remove: render_operation_flowchart,
	operation: copy_operation_relation_defaults,
	sequence_id: render_operation_flowchart,
	predecessor_relation: render_operation_flowchart,
	lag_mins: render_operation_flowchart,
	time_in_mins: render_operation_flowchart,
	workstation: render_operation_flowchart,
}

frappe.ui.form.on('BOM', parent_handlers)
frappe.ui.form.on('Routing', parent_handlers)
frappe.ui.form.on('Work Order', parent_handlers)
frappe.ui.form.on('BOM Operation', operation_row_handlers)
frappe.ui.form.on('Work Order Operation', operation_row_handlers)
