frappe.ui.form.on('Work Order', {
	setup: function (frm) {
		frm.custom_make_buttons = {
			'New Subcontract PO': 'Create Subcontract PO',
			'Add to Existing PO': 'Add to Existing PO',
		}
	},

	refresh: function (frm) {
		if (frm.doc.company && frm.doc.docstatus == 1) {
			frappe.db.get_value('Item', { item_code: frm.doc.production_item }, 'is_sub_contracted_item').then(r => {
				if (r && r.message && r.message.is_sub_contracted_item) {
					frappe.db
						.get_value('Inventory Tools Settings', { company: frm.doc.company }, 'enable_work_order_subcontracting')
						.then(r => {
							if (r && r.message && r.message.enable_work_order_subcontracting) {
								frm.add_custom_button(
									__('Create Subcontract PO'),
									() => {
										frappe.xcall('inventory_tools.overrides.work_order.make_subcontracted_purchase_order', {
											wo_name: frm.doc.name,
										})
									},
									__('Subcontracting')
								)

								frm.add_custom_button(
									__('Add to Existing PO'),
									() => {
										let d = new frappe.ui.Dialog({
											title: __('Add to Purchase Order'),
											fields: [
												{
													label: __('Purchase Order'),
													fieldname: 'purchase_order',
													fieldtype: 'Link',
													options: 'Purchase Order',
													reqd: 1,
												},
											],
											primary_action: function () {
												let data = d.get_values()
												frappe
													.xcall('inventory_tools.overrides.work_order.add_to_existing_purchase_order', {
														wo_name: frm.doc.name,
														po_name: data.purchase_order,
													})
													.then(r => {
														d.hide()
													})
											},
											primary_action_label: __('Add to PO'),
										})
										d.show()
										d.fields_dict.purchase_order.get_query = () => {
											return {
												filters: {
													is_subcontracted: 1,
													docstatus: ['!=', 2],
													// TODO: can date filters in dialog be used to filter purchase orders?
												},
											}
										}
									},
									__('Subcontracting')
								)
							}
						})
				}
			})
		}
	},
})
