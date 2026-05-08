# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Backfill Physical Dimension.item_uom from linked Item.stock_uom for Item references."""

	pd_table = frappe.qb.DocType("Physical Dimension")
	item_table = frappe.qb.DocType("Item")

	if frappe.conf.db_type == "postgres":
		query = (
			frappe.qb.update(pd_table)
			.set(pd_table.item_uom, item_table.stock_uom)
			.from_(item_table)
			.where(
				(pd_table.reference_doctype == "Item") & (item_table.name == pd_table.reference_document)
			)
		)
	else:
		query = (
			frappe.qb.update(pd_table)
			.inner_join(item_table)
			.on(item_table.name == pd_table.reference_document)
			.set(pd_table.item_uom, item_table.stock_uom)
			.where(pd_table.reference_doctype == "Item")
		)

	query.run()
