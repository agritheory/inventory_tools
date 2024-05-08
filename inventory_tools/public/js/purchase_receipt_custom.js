// Code for Purchase Taxes and Charges ("taxes") child table
frappe.ui.form.on('Purchase Taxes and Charges', {
	taxes_add: function (frm, cdt, cdn) {
		// Set the tax category based on "distribute_charges_based_on" selection
		let child = locals[cdt][cdn]
		let category = 'Total'

		if (frm.doc.distribute_charges_based_on != "Don't Distribute") {
			category = 'Valuation and Total'
		}
		frappe.model.set_value(child.doctype, child.name, 'category', category)
	},
	taxes_remove: function (frm, cdt, cdn) {
		calc_landed_costs(frm)
	},
	category: function (frm, cdt, cdn) {
		calc_landed_costs(frm)
	},
	tax_amount: function (frm, cdt, cdn) {
		let child = locals[cdt][cdn]

		// Temporarily set value so functions have updated information when called
		child.tax_amount_after_discount_amount = child.tax_amount
		calc_landed_costs(frm)
	},
})

// Code for Purchase Receipt Item ("items") child table
frappe.ui.form.on('Purchase Receipt Item', {
	qty: function (frm, cdt, cdn) {
		// Re-calculate landed_costs and item_total fields on item quantity change
		let child = locals[cdt][cdn]
		let updated_base_net_amount = child.qty * child.rate

		// Temporarily set value so functions have updated information when called
		child.base_net_amount = updated_base_net_amount
		calc_landed_costs(frm)
	},
	items_add: function (frm, cdt, cdn) {
		frappe.run_serially([
			async () => {
				await fetch_asset_or_stock(frm)
			},
			() => {
				calc_landed_costs(frm)
			},
		])
	},
	items_remove: function (frm, cdt, cdn) {
		calc_landed_costs(frm)
	},
})

frappe.ui.form.on('Purchase Receipt', {
	refresh: frm => {
		show_landed_cost_fields(frm)
	},
	validate: frm => {
		frappe.run_serially([
			async () => {
				await fetch_asset_or_stock(frm)
			},
			() => {
				calc_landed_costs(frm)
			},
		])
	},
	distribute_charges_based_on: frm => {
		toggle_landed_cost_columns(frm)
		if (!frm.doc.taxes || frm.doc.distribute_charges_based_on == "Don't Distribute") {
			// No tax items or not distributing them, reset landed_costs and item_total fields
			reset_landed_costs(frm)
			set_tax_category(frm)
		} else {
			// Tax items exist, set each tax's category to align with dropdown selection
			frappe.run_serially([
				async () => {
					await fetch_asset_or_stock(frm)
				},
				() => {
					set_tax_category(frm)
				},
				() => {
					calc_landed_costs(frm)
				},
			])
		}
	},
})

function show_landed_cost_fields(frm) {
	if (!frm.doc.company) {
		hide_field('distribute_charges_based_on')
		hide_field('total_with_landed_costs')
		toggle_landed_cost_columns(frm)
		return
	}
	frappe.db
		.get_value('Inventory Tools Settings', { company: frm.doc.company }, 'enable_inline_landed_costing')
		.then(r => {
			if (r && r.message && r.message.enable_inline_landed_costing) {
				unhide_field('distribute_charges_based_on')
				unhide_field('total_with_landed_costs')
			} else {
				hide_field('distribute_charges_based_on')
				hide_field('total_with_landed_costs')
			}
			toggle_landed_cost_columns(frm)
		})
}

function set_tax_category(frm) {
	if (frm.doc.taxes.length) {
		// Set tax category based on dropdown selection
		frm.doc.taxes.forEach(tax => {
			tax.category = frm.doc.distribute_charges_based_on == "Don't Distribute" ? 'Total' : 'Valuation and Total'
		})
	}
}

function reset_landed_costs(frm) {
	let total_with_landed_costs = 0.0
	if (frm.doc.items.length) {
		frm.doc.items.forEach(item => {
			item.landed_costs = 0
			item.item_total = item.base_net_amount
			total_with_landed_costs = total_with_landed_costs + item.base_net_amount
		})
	}
	frm.set_value('total_with_landed_costs', total_with_landed_costs)
	frm.refresh_fields(['items', 'total_with_landed_costs'])
}

function calc_landed_costs(frm) {
	let stock_or_asset_items = frm.doc.items.filter(item => item.is_stock_item || item.is_fixed_asset)
	if (stock_or_asset_items.length == 0) {
		reset_landed_costs(frm)
		frappe.throw(
			__(
				'No items are stock or asset items (a requirement to update item valuations). ' +
					"Please change 'Distribute Landed Cost Charges Based On' to Don't Distribute." +
					"If an item should be a stock item, select 'Maintain Stock' in its Item Master."
			)
		)
	}

	if (stock_or_asset_items.length && frm.doc.taxes.length) {
		// There are stock items as well as taxes to distribute to them
		let last_idx = stock_or_asset_items[stock_or_asset_items.length - 1].idx
		let total_taxes = frm.doc.taxes.reduce((init_val, tax) => {
			return init_val + (tax.category == 'Total' ? 0.0 : tax.tax_amount_after_discount_amount) // only include where category is Valuation-related
		}, 0.0)
		let total_qty = stock_or_asset_items.reduce((init_val, item) => {
			return init_val + item.qty
		}, 0.0)
		let total_amount = stock_or_asset_items.reduce((init_val, item) => {
			return init_val + item.base_net_amount
		}, 0.0)
		let div_by_zero_flag = (frm.doc.based_on == 'Qty' && !total_qty) || (frm.doc.based_on == 'Amount' && !total_amount)
		let valuation_amount_adjustment = total_taxes
		let total_lc = 0.0

		if (frm.doc.distribute_charges_based_on == "Don't Distribute") {
			reset_landed_costs(frm)
		} else {
			if (div_by_zero_flag) {
				let field = frm.doc.distribute_charges_based_on == 'Qty' ? 'Accepted Quantity' : 'Amount'
				frappe.throw(__(field + " values can't total zero when distributing charges based on " + frm.doc.based_on))
			} else {
				// Loop over items, set landed costs for stock items (0 for non-stock) and update item total
				frm.doc.items.forEach(item => {
					if (!item.is_stock_item && !item.is_fixed_asset) {
						item.landed_costs = 0.0
					} else if (item.idx == last_idx) {
						// Last stock item, set landed_costs to remaining tax amount
						let lc = valuation_amount_adjustment >= 0 ? valuation_amount_adjustment : 0
						item.landed_costs = Number(lc.toFixed(2))
					} else {
						let p =
							frm.doc.distribute_charges_based_on == 'Qty' ? item.qty / total_qty : item.base_net_amount / total_amount
						item.landed_costs = Number((p * total_taxes).toFixed(2))
						valuation_amount_adjustment = valuation_amount_adjustment - item.landed_costs
					}
					total_lc = total_lc + item.landed_costs
					item.item_total = item.base_net_amount + item.landed_costs
				})

				// Calculate any rounding difference and add to last stock item
				let diff = Number((total_taxes - total_lc).toFixed(2))
				if (Math.abs(diff) >= 0.01) {
					frm.doc.items.forEach(item => {
						if (item.idx == last_idx) {
							item.landed_costs = item.landed_costs + diff
						}
					})
				}
				let total_with_landed_costs = frm.doc.items.reduce((init_val, item) => {
					return init_val + item.item_total
				}, 0.0)
				frm.set_value('total_with_landed_costs', total_with_landed_costs)
				frm.refresh_fields(['items', 'total_with_landed_costs'])
			}
		}
	} else {
		// No taxes and/or no stock items
		reset_landed_costs(frm)
	}
}

async function fetch_asset_or_stock(frm) {
	for await (const item of frm.doc.items) {
		await frappe.db.get_value('Item', item.item_code, ['is_stock_item', 'is_fixed_asset']).then(r => {
			item.is_stock_item = r.message.is_stock_item
			item.is_fixed_asset = r.message.is_fixed_asset
		})
	}
	frm.refresh_field('items')
}

function toggle_landed_cost_columns(frm) {
	if (frm.doc.distribute_charges_based_on == "Don't Distribute") {
		// hide columns
		frm.get_field('items').grid.reset_grid()
		frm.get_field('items').grid.visible_columns.forEach((column, index) => {
			if (index >= frm.get_field('items').grid.visible_columns.length - 2) {
				column[0].columns = 2
				column[1] = 2
			}
		})
		for (let row of frm.get_field('items').grid.grid_rows) {
			if (row.open_form_button) {
				row.open_form_button.parent().remove()
				delete row.open_form_button
			}

			for (let field in row.columns) {
				if (row.columns[field] !== undefined) {
					row.columns[field].remove()
				}
			}
			delete row.columns
			row.columns = []
			row.render_row()
		}
	} else {
		// show landed cost
		frm.get_field('items').grid.reset_grid()
		let user_defined_columns = frm.get_field('items').grid.visible_columns.map(col => {
			return col[0]
		})
		user_defined_columns.forEach((column, index) => {
			if (index > 0) {
				column.columns = 1
			}
		})
		let landed_costs = frappe.meta.get_docfield(frm.get_field('items').grid.doctype, 'landed_costs')
		landed_costs.in_list_view = 1
		user_defined_columns.push(landed_costs)
		let item_total = frappe.meta.get_docfield(frm.get_field('items').grid.doctype, 'item_total')
		item_total.in_list_view = 1
		user_defined_columns.push(item_total)
		frm.get_field('items').grid.visible_columns = user_defined_columns.map(col => {
			return [col, col.columns]
		})
		for (let row of frm.get_field('items').grid.grid_rows) {
			if (row.open_form_button) {
				row.open_form_button.parent().remove()
				delete row.open_form_button
			}

			for (let field in row.columns) {
				if (row.columns[field] !== undefined) {
					row.columns[field].remove()
				}
			}
			delete row.columns
			row.columns = []
			row.render_row()
		}
	}
	frm.get_field('items').refresh()
}
