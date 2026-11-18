// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

import { createApp, reactive } from 'vue'

import OperationFlowchart from './OperationFlowchart.vue'

frappe.provide('inventory_tools')

const RENDER_DELAY_MS = 300

inventory_tools.render_operation_flowchart = frm => {
	const field = frm.fields_dict.operation_flowchart
	if (!field) {
		return
	}
	const flowchart = get_or_mount_flowchart(frm, field)
	clearTimeout(flowchart.timer)
	flowchart.timer = setTimeout(() => fetch_flowchart(frm, flowchart), RENDER_DELAY_MS)
}

function get_or_mount_flowchart(frm, field) {
	const wrapper = field.$wrapper.get(0)
	if (wrapper.operation_flowchart) {
		wrapper.operation_flowchart.frm = frm
		return wrapper.operation_flowchart
	}
	const state = reactive({ data: null, loading: false, error: null })
	const flowchart = { frm, state, timer: null, request: 0 }
	const target = document.createElement('div')
	field.$wrapper.empty().append(target)
	createApp(OperationFlowchart, {
		state,
		onSelect: key => select_operation_row(flowchart.frm, key),
	}).mount(target)
	wrapper.operation_flowchart = flowchart
	return flowchart
}

function fetch_flowchart(frm, flowchart) {
	const { state } = flowchart
	if (!(frm.doc.operations || []).length) {
		state.data = null
		state.error = null
		return
	}
	const request = ++flowchart.request
	const unsaved = frm.is_new() || frm.is_dirty()
	state.loading = true
	frappe
		.call({
			method: 'inventory_tools.inventory_tools.scheduling.flowchart.get_operation_flowchart',
			args: {
				doctype: frm.doctype,
				name: unsaved ? null : frm.doc.name,
				doc: unsaved ? JSON.stringify(frm.doc) : null,
			},
		})
		.then(r => {
			if (request !== flowchart.request) {
				return
			}
			state.data = r.message
			state.error = null
		})
		.catch(() => {
			if (request === flowchart.request) {
				state.error = __('Could not load the operation flowchart.')
			}
		})
		.finally(() => {
			if (request === flowchart.request) {
				state.loading = false
			}
		})
}

function select_operation_row(frm, key) {
	const grid_row = frm.fields_dict.operations?.grid?.grid_rows_by_docname?.[key]
	if (!grid_row) {
		return
	}
	frm.scroll_to_field('operations')
	grid_row.toggle_view(true)
}
