function getSearchComponents(doctype) {
	frappe.ready(() => {
		frappe.call({
			method: 'inventory_tools.inventory_tools.faceted_search.show_faceted_search_components',
			args: { doctype: 'Item' },
			headers: { 'X-Frappe-CSRF-Token': frappe.csrf_token },
			callback: r => {
				return r
			},
		})
	})
}

module.exports = {
	getSearchComponents,
}
