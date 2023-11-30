// Copyright (c) 2023, AgriTheory and contributors
// For license information, please see license.txt

frappe.query_reports['Specification'] = {
	filters: [
		{
			fieldname: 'specification',
			label: __('Specification'),
			options: 'Specification',
			fieldtype: 'Link',
			reqd: 1,
		},
	],
	refresh: reportview => {
		this.get_datatable_options(frappe.query_report.datatable.options)
	},
	get_datatable_options(options) {
		options.columns[3].editable = true
		return Object.assign(options, {
			getEditor: this.get_editing_object.bind(this),
		})
	},
	get_editing_object(colIndex, rowIndex, value, parent) {
		if (frappe.query_report.datatable.datamanager.data[rowIndex].field != undefined) {
			frappe.show_alert(__('This value cannot be edited in this report'))
			return false
		}
		const control = this.render_editing_input(colIndex, value, parent)
		if (!control) return false
		control.df.change = () => control.set_focus()
		try {
			return {
				initValue: async value => {
					return control.set_value(value)
				},
				setValue: value => {
					let row = frappe.query_report.datatable.datamanager.data[rowIndex]
					let docname = row.name
					if (!value) {
						return control.get_value()
					}
					if (row.indent === 0) {
						return control.get_value()
					}
					if (row.billed_date) {
						return control.get_value()
					}

					return frappe
						.xcall('inventory_tools.inventory_tools.report.specification.specification.set_value', {
							docname: docname,
							value: value,
						})
						.catch(e => {
							return control.get_value(value)
						})
				},
				getValue: async () => {
					return control.get_value()
				},
			}
		} catch (error) {
			console.log(error)
		}
	},
	render_editing_input(colIndex, value, parent) {
		const col = frappe.query_report.datatable.getColumn(colIndex)
		let control = null
		control = frappe.ui.form.make_control({
			df: col,
			parent: parent,
			render_input: true,
		})
		control.set_value(value || '')
		control.toggle_label(false)
		control.toggle_description(false)
		return control
	},
}
