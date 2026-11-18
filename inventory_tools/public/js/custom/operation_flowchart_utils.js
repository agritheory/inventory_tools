// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

const OPERATION_RELATION_ROW_FIELDS = ['predecessor_relation', 'lag_mins']

// A company without settings counts as enabled, matching the field default.
function operation_relations_enabled(company) {
	const settings_by_company = frappe.boot.inventory_tools_settings || {}
	if (company) {
		const settings = settings_by_company[company]
		return !settings || Boolean(settings.enable_operation_relations)
	}
	const all_settings = Object.values(settings_by_company)
	return !all_settings.length || all_settings.some(settings => settings.enable_operation_relations)
}

function toggle_operation_relations(frm, enabled) {
	frm.toggle_display('operation_flowchart', enabled)
	const grid = frm.fields_dict.operations?.grid
	if (!grid) {
		return
	}
	OPERATION_RELATION_ROW_FIELDS.forEach(fieldname => {
		grid.update_docfield_property(fieldname, 'hidden', enabled ? 0 : 1)
	})
	grid.refresh()
}

function render_operation_flowchart(frm) {
	const enabled = operation_relations_enabled(frm.doc.company)
	if (frm.operation_relations_enabled !== enabled) {
		frm.operation_relations_enabled = enabled
		toggle_operation_relations(frm, enabled)
	}
	if (enabled && inventory_tools.render_operation_flowchart) {
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
	company: render_operation_flowchart,
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
