function getSearchComponents(doctype) {
	frappe
		.xcall('inventory_tools.inventory_tools.faceted_search.show_faceted_search_components', { doctype: 'Item' })
		.then(r => {
			console.log(r)
			return r
		})
}

module.exports = {
	getSearchComponents,
}
