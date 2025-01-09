// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.treeview_settings['Warehouse'] = {
	get_tree_nodes: 'inventory_tools.inventory_tools.overrides.warehouse.get_children',
	add_tree_node: 'erpnext.stock.doctype.warehouse.warehouse.add_node',
	get_tree_root: false,
	root_label: 'Warehouses',
	filters: [
		{
			fieldname: 'company',
			fieldtype: 'Select',
			options: erpnext.utils.get_tree_options('company'),
			label: __('Company'),
			default: erpnext.utils.get_tree_default('company'),
		},
	],
	fields: [
		{ fieldtype: 'Data', fieldname: 'warehouse_name', label: __('New Warehouse Name'), reqd: true },
		{
			fieldtype: 'Check',
			fieldname: 'is_group',
			label: __('Is Group'),
			description: __("Child nodes can be only created under 'Group' type nodes"),
		},
	],
	ignore_fields: ['parent_warehouse'],
	onrender: node => {
		if (
			cur_tree &&
			frappe.boot.inventory_tools_settings[cur_tree.args.company] &&
			frappe.boot.inventory_tools_settings[cur_tree.args.company].prettify_warehouse_tree
		) {
			if (node.data.disabled) {
				let n = node.$tree_link.find('.tree-label')
				$(n[0]).css({ 'text-decoration': 'line-through' })
			}
			if (!node.data.is_group && node.data.warehouse_type && node.data.icon) {
				node.$tree_link.find('.icon use').attr('href', `#icon-${node.data.icon}`)
			}
		}
	},
}
