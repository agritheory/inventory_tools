# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.query_builder import DocType

from inventory_tools.inventory_tools.uom_conversion_exceptions import (
	DEFAULT_SCAN_SPECS,
	ScanSpec,
	factor_categories_for_uoms,
	is_undocumented_line_uom,
	load_item_meta,
	load_uom_conversion_detail_pairs,
	normalize_multiselect_filter,
	row_matches_category_filter,
	row_matches_uom_filter,
)


def execute(filters: dict | None = None):
	filters = filters or {}
	selected_uoms = normalize_multiselect_filter(filters.get("uom"))
	selected_categories = normalize_multiselect_filter(filters.get("uom_category"))
	company = filters.get("company")
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	columns = get_columns()
	raw_rows: list[dict] = []
	for spec in DEFAULT_SCAN_SPECS:
		raw_rows.extend(_query_spec_rows(spec, company, from_date, to_date))

	if not raw_rows:
		return columns, []

	item_codes = {r["item_code"] for r in raw_rows if r.get("item_code")}
	item_meta = load_item_meta(item_codes)
	detail_pairs = load_uom_conversion_detail_pairs(item_codes, item_meta)

	candidates: list[dict] = []
	for r in raw_rows:
		code = r.get("item_code")
		if not code or code not in item_meta:
			continue
		line_uom = r.get("line_uom")
		if not line_uom:
			continue
		row_stock = r.get("row_stock_uom") or ""
		stock_uom = row_stock or (item_meta[code].get("stock_uom") or "")
		if not stock_uom or line_uom == stock_uom:
			continue
		r["_norm_stock_uom"] = stock_uom
		candidates.append(r)

	if not candidates:
		return columns, []

	uoms_for_cats = {c["_norm_stock_uom"] for c in candidates} | {c["line_uom"] for c in candidates}
	uom_to_cats = factor_categories_for_uoms(uoms_for_cats)

	out: list[dict] = []
	for r in candidates:
		stock_uom = r["_norm_stock_uom"]
		line_uom = r["line_uom"]
		if not row_matches_uom_filter(selected_uoms, line_uom, stock_uom):
			continue
		if not row_matches_category_filter(selected_categories, line_uom, stock_uom, uom_to_cats):
			continue
		if not is_undocumented_line_uom(r["item_code"], line_uom, stock_uom, item_meta, detail_pairs):
			continue

		meta_row = item_meta[r["item_code"]]
		out.append(
			{
				"parenttype": r["parenttype"],
				"parent": r["parent"],
				"transaction_date": r.get("transaction_date"),
				"child_row_name": r.get("child_row_name"),
				"child_idx": r.get("child_idx"),
				"item_code": r["item_code"],
				"item_name": meta_row.get("item_name") or "",
				"line_uom": line_uom,
				"stock_uom": stock_uom,
				"row_conversion_factor": r.get("row_conversion_factor"),
				"reason": _("No Item UOM Conversion Detail and no global UOM Conversion Factor"),
			}
		)

	return columns, out


def get_columns():
	return [
		{
			"label": _("Parent DocType"),
			"fieldname": "parenttype",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Document"),
			"fieldname": "parent",
			"fieldtype": "Dynamic Link",
			"options": "parenttype",
			"width": 160,
		},
		{"label": _("Date"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 110},
		{
			"label": _("Row name"),
			"fieldname": "child_row_name",
			"fieldtype": "Data",
			"width": 130,
		},
		{"label": _("Row idx"), "fieldname": "child_idx", "fieldtype": "Int", "width": 70},
		{
			"label": _("Item"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 140,
		},
		{"label": _("Item name"), "fieldname": "item_name", "fieldtype": "Data", "width": 180},
		{
			"label": _("Line UOM"),
			"fieldname": "line_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
		},
		{
			"label": _("Stock UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
		},
		{
			"label": _("Stored conv. factor"),
			"fieldname": "row_conversion_factor",
			"fieldtype": "Float",
			"width": 120,
		},
		{"label": _("Reason"), "fieldname": "reason", "fieldtype": "Data", "width": 360},
	]


def _query_spec_rows(
	spec: ScanSpec, company: str | None, from_date, to_date
) -> list[dict[str, object]]:
	child_meta = frappe.get_meta(spec.child_doctype)
	child = DocType(spec.child_doctype)
	parent = DocType(spec.parent_doctype)

	date_col = getattr(parent, spec.date_field)
	select_fields: list = [
		child.name.as_("child_row_name"),
		child.idx.as_("child_idx"),
		child.parent,
		child.item_code,
		child.uom.as_("line_uom"),
		child.stock_uom.as_("row_stock_uom"),
		date_col.as_("transaction_date"),
	]
	if child_meta.get_field("conversion_factor"):
		select_fields.append(child.conversion_factor.as_("row_conversion_factor"))

	q = (
		frappe.qb.from_(child).inner_join(parent).on(child.parent == parent.name).select(*select_fields)
	)

	conds = (
		(parent.docstatus == 1)
		& (child.parenttype == spec.parent_doctype)
		& (child.item_code.isnotnull())
		& (child.item_code != "")
		& (child.uom.isnotnull())
		& (child.uom != "")
		& ((child.stock_uom.isnull()) | (child.uom != child.stock_uom))
	)
	if spec.company_field and company:
		conds &= getattr(parent, spec.company_field) == company
	if from_date:
		conds &= date_col >= from_date
	if to_date:
		conds &= date_col <= to_date

	rows = q.where(conds).run(as_dict=True)
	for r in rows:
		r["parenttype"] = spec.parent_doctype
		if "row_conversion_factor" not in r:
			r["row_conversion_factor"] = None
	return rows
