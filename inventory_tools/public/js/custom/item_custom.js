frappe.ui.form.on('Item', {
	refresh: frm => {
		add_specification_dialog(frm)
	},
})

function add_specification_dialog(frm) {
	// save before continuing
	frm.add_custom_button(
		'Edit Specification',
		() => {
			specification_dialog(frm)
		},
		'Actions'
	)
}

async function specification_dialog(frm) {
	const data = await get_specifications(frm)
	let current_spec = data[0].specification
	let attributes = data.map(r => r.attribute)
	let fields = [
		{
			fieldtype: 'Data',
			fieldname: 'row_name',
			in_list_view: 0,
			read_only: 1,
			disabled: 0,
			hidden: 1,
		},
		{
			fieldtype: 'Select',
			fieldname: 'attribute',
			in_list_view: 1,
			read_only: 0,
			disabled: 0,
			label: __('Attribute'),
			options: attributes,
		},
		{
			fieldtype: 'Data',
			fieldname: 'field',
			label: __('Field'),
			in_list_view: 1,
			read_only: 1,
		},
		{
			fieldtype: 'Data',
			fieldname: 'value',
			label: __('Value'),
			in_list_view: 1,
			read_only: 0,
		},
	]
	return new Promise(resolve => {
		let d = new frappe.ui.Dialog({
			title: __('Edit Specifications'),
			fields: [
				{
					label: __('Specification'),
					fieldname: 'specification',
					fieldtype: 'Link',
					options: 'Specification',
					default: current_spec,
				},
				{
					fieldtype: 'Column Break',
					fieldname: 'col_break_1',
				},
				{
					fieldtype: 'Section Break',
					fieldname: 'section_break_1',
				},
				{
					fieldname: 'specs',
					fieldtype: 'Table',
					in_place_edit: true,
					editable_grid: true,
					reqd: 1,
					data: data,
					get_data: () => get_specifications(frm),
					fields: fields,
				},
			],
			primary_action: () => {
				let values = d.get_values()
				if (!values) {
					return
				}
				frappe.xcall(
					'inventory_tools.inventory_tools.doctype.specification.specification.update_specification_values',
					{
						reference_doctype: frm.doc.doctype,
						reference_name: frm.doc.name,
						spec: values.specification,
						specifications: values.specs,
					}
				)
				resolve(d.hide())
			},
			primary_action_label: __('Save'),
			size: 'large',
		})
		d.show()
	})
}

async function get_specifications(frm) {
	let r = await frappe.xcall(
		'inventory_tools.inventory_tools.doctype.specification.specification.get_specification_values',
		{
			reference_doctype: frm.doc.doctype,
			reference_name: frm.doc.name,
		}
	)
	return r
}
