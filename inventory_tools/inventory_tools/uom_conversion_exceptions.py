# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from collections.abc import Callable, Iterable

import frappe
from frappe import _
from frappe.query_builder import DocType

from erpnext.stock.doctype.item.item import get_uom_conv_factor

NOT_CATEGORIZED_SENTINEL = "__IT_NOT_CATEGORIZED__"


@dataclass(frozen=True, slots=True)
class ScanSpec:
	child_doctype: str
	parent_doctype: str
	"""Date field on parent for from/to filters."""
	date_field: str
	"""Field on parent for company filter; None if parent has no company."""
	company_field: str | None = "company"


# High-volume transactional child tables with item_code + uom + stock_uom (ERPNext stock flow).
DEFAULT_SCAN_SPECS: tuple[ScanSpec, ...] = (
	ScanSpec("Sales Order Item", "Sales Order", "transaction_date", "company"),
	ScanSpec("Delivery Note Item", "Delivery Note", "posting_date", "company"),
	ScanSpec("Purchase Order Item", "Purchase Order", "transaction_date", "company"),
	ScanSpec("Purchase Receipt Item", "Purchase Receipt", "posting_date", "company"),
	ScanSpec("Material Request Item", "Material Request", "transaction_date", "company"),
	ScanSpec("Stock Entry Detail", "Stock Entry", "posting_date", "company"),
	ScanSpec("Quotation Item", "Quotation", "transaction_date", "company"),
	ScanSpec("Sales Invoice Item", "Sales Invoice", "posting_date", "company"),
	ScanSpec("Purchase Invoice Item", "Purchase Invoice", "posting_date", "company"),
)


def normalize_multiselect_filter(value: Any) -> list[str]:
	if value in (None, "", []):
		return []
	if isinstance(value, str):
		try:
			parsed = json.loads(value)
		except json.JSONDecodeError:
			return [value] if value.strip() else []
		value = parsed
	if not isinstance(value, (list, tuple)):
		return []
	out: list[str] = []
	for x in value:
		if x is None:
			continue
		s = str(x).strip()
		if s:
			out.append(s)
	return out


def factor_categories_for_uoms(uoms: Iterable[str]) -> dict[str, set[str]]:
	"""Map each UOM name to distinct UOM Conversion Factor category names it appears in."""
	names = {u for u in uoms if u}
	if not names:
		return {}
	ucf = DocType("UOM Conversion Factor")
	nlist = list(names)
	fr = getattr(ucf, "from_uom")
	to = getattr(ucf, "to_uom")
	cat = getattr(ucf, "category")
	q1 = frappe.qb.from_(ucf).select(fr.as_("uom_name"), cat).where(fr.isin(nlist))
	q2 = frappe.qb.from_(ucf).select(to.as_("uom_name"), cat).where(to.isin(nlist))
	rows = q1.union(q2).run()
	result: dict[str, set[str]] = {u: set() for u in names}
	for uom_name, category in rows:
		if uom_name in result and category:
			result[uom_name].add(category)
	return result


def load_item_meta(item_codes: Iterable[str]) -> dict[str, dict[str, Any]]:
	codes = [c for c in {x for x in item_codes if x} if frappe.db.exists("Item", c)]
	if not codes:
		return {}
	rows = frappe.get_all(
		"Item",
		filters={"name": ("in", codes)},
		fields=["name", "item_name", "stock_uom", "variant_of", "is_stock_item"],
		as_list=False,
	)
	return {r.name: r for r in rows}


def load_uom_conversion_detail_pairs(
	item_codes: Iterable[str], item_meta: dict[str, dict[str, Any]]
) -> set[tuple[str, str]]:
	parents: set[str] = set()
	for code in item_codes:
		if code not in item_meta:
			continue
		parents.add(code)
		v = item_meta[code].get("variant_of")
		if v:
			parents.add(v)
	if not parents:
		return set()
	rows = frappe.get_all(
		"UOM Conversion Detail",
		filters={"parent": ("in", list(parents))},
		fields=["parent", "uom"],
	)
	return {(r.parent, r.uom) for r in rows if r.uom}


def item_has_conversion_detail(
	item_code: str,
	line_uom: str,
	item_meta: dict[str, dict[str, Any]],
	detail_pairs: set[tuple[str, str]],
) -> bool:
	meta = item_meta.get(item_code)
	if not meta:
		return False
	for parent_key in (item_code, meta.get("variant_of")):
		if parent_key and (parent_key, line_uom) in detail_pairs:
			return True
	return False


def global_uom_conversion_resolves(line_uom: str, stock_uom: str) -> bool:
	if line_uom == stock_uom:
		return True
	f = get_uom_conv_factor(line_uom, stock_uom)
	return f is not None


def is_undocumented_line_uom(
	item_code: str,
	line_uom: str,
	stock_uom: str,
	item_meta: dict[str, dict[str, Any]],
	detail_pairs: set[tuple[str, str]],
	_global_check: Callable[[str, str], bool] | None = None,
) -> bool:
	"""
	True when ERPNext would fall back to conversion_factor 1.0 with no backing detail/global factor.
	"""
	if not item_code or not line_uom:
		return False
	meta = item_meta.get(item_code)
	if not meta or not meta.get("is_stock_item"):
		return False
	if line_uom == stock_uom:
		return False
	if item_has_conversion_detail(item_code, line_uom, item_meta, detail_pairs):
		return False
	check = _global_check or global_uom_conversion_resolves
	return not check(line_uom, stock_uom)


def row_matches_uom_filter(selected_uoms: list[str], line_uom: str, stock_uom: str) -> bool:
	if not selected_uoms:
		return True
	sel = set(selected_uoms)
	return line_uom in sel or stock_uom in sel


def row_matches_category_filter(
	selected: list[str], line_uom: str, stock_uom: str, uom_to_cats: dict[str, set[str]]
) -> bool:
	if not selected:
		return True
	line_cats = uom_to_cats.get(line_uom, set())
	stock_cats = uom_to_cats.get(stock_uom, set())
	for token in selected:
		if token == NOT_CATEGORIZED_SENTINEL:
			if not line_cats or not stock_cats:
				return True
		elif token in line_cats or token in stock_cats:
			return True
	return False


@frappe.whitelist()
def category_filter_multiselect_data(txt: str | None = None) -> list[dict[str, str]]:
	"""Link-style options for UOM Category multiselect plus synthetic not-in-table row."""
	frappe.has_permission("UOM Category", "read", throw=True)
	sentinel = {
		"value": NOT_CATEGORIZED_SENTINEL,
		"description": _("Not in any conversion factor"),
	}
	opts = frappe.db.get_link_options("UOM Category", (txt or "").strip(), None) or []
	return [sentinel, *opts]
