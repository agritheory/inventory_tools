// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.provide('inventory_tools.alternative_workstation')

inventory_tools.alternative_workstation.get_work_order_from_url = function () {
	const params = new URLSearchParams(window.location.search)
	const from_query = params.get('work_order')
	if (from_query) {
		return from_query
	}
	const route = frappe.get_route() || []
	if (route[0] === 'alternative-workstation' && route[1]) {
		return route[1]
	}
	if (frappe.route_options && frappe.route_options.work_order) {
		return frappe.route_options.work_order
	}
	return null
}

inventory_tools.alternative_workstation.set_work_order_url = function (work_order) {
	const base = '/app/alternative-workstation'
	const url = work_order ? `${base}?work_order=${encodeURIComponent(work_order)}` : base
	if (window.location.pathname + window.location.search !== url) {
		history.replaceState(null, '', url)
	}
}

inventory_tools.alternative_workstation.open = function (work_order) {
	if (work_order) {
		history.pushState(null, '', '/app/alternative-workstation?work_order=' + encodeURIComponent(work_order))
	} else {
		history.pushState(null, '', '/app/alternative-workstation')
	}
	frappe.router.route()
}
