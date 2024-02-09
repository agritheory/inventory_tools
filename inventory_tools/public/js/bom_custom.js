frappe.ui.form.on('BOM', {
	refresh: frm => {
		
	},
})
cur_frm.fields_dict["operations"].grid.get_field("workstation").get_query = function(doc,cdt,cdn) {
	var d = locals[cdt][cdn]
	return {
		query: "inventory_tools.api.get_alternative_workstations",
		filters: {
			operation: d.operation
		}
	}
}