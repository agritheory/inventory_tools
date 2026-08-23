# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.model.meta import get_parent_dt
from frappe.model.rename_doc import get_link_fields


def transactional_uom_link_parent(parent_dt: str) -> bool:
	if parent_dt == "Item":
		return True
	row = frappe.db.get_value(
		"DocType", parent_dt, ["istable", "is_submittable", "issingle"], as_dict=True
	)
	if not row or row.get("issingle"):
		return False
	if row.get("istable"):
		pn = get_parent_dt(parent_dt)
		return bool(pn and frappe.db.get_value("DocType", pn, "is_submittable"))
	return bool(row.get("is_submittable"))


def collect_transactional_item_uom_link_branches(include_field=None) -> list[tuple[str, str]]:
	meta_fields: dict[tuple[str, str], dict] = {}
	for crow in get_link_fields("UOM"):
		meta_fields.setdefault((crow["parent"], crow["fieldname"]), crow)
	if include_field:
		meta_fields.setdefault(include_field, {"issingle": 0})

	branches: list[tuple[str, str]] = []
	table_missing = getattr(type(frappe.db), "TableMissingError", ())

	for parent_dt, fieldname in sorted(meta_fields.keys()):
		row_meta = meta_fields[(parent_dt, fieldname)]
		if row_meta.get("issingle") or parent_dt == "UOM Conversion Factor":
			continue
		if not transactional_uom_link_parent(parent_dt):
			continue
		try:
			if not frappe.db.has_column(parent_dt, fieldname):
				continue
		except Exception as err:
			if table_missing and isinstance(err, table_missing):
				continue
			raise
		branches.append((parent_dt, fieldname))

	return branches


def validated_categories_argument(categories) -> list[str]:
	if isinstance(categories, str):
		try:
			categories = json.loads(categories)
		except json.JSONDecodeError:
			categories = [categories]
	if not isinstance(categories, (list, tuple)) or not categories:
		frappe.throw(_("Provide a list of UOM Category names."))

	validated = []
	for c in categories:
		if not c or not isinstance(c, str):
			frappe.throw(_("Invalid category entry."))
		if not frappe.db.exists("UOM Category", c):
			frappe.throw(_("Unknown UOM Category: {0}").format(c))
		validated.append(c)
	return validated


def unused_uom_names(validated_categories: list[str]) -> list[str]:
	cat_names = conversion_uoms_for_categories(validated_categories)
	txn_used = transactional_uom_refs(cat_names)
	cross_used = conversion_uoms_outside_categories(validated_categories, cat_names)
	return sorted(cat_names - txn_used - cross_used)


def conversion_uoms_for_categories(categories: list[str]) -> set[str]:
	ucf = frappe.qb.DocType("UOM Conversion Factor")
	fr = getattr(ucf, "from_uom")
	to = getattr(ucf, "to_uom")
	wc = ucf.category == categories[0] if len(categories) == 1 else ucf.category.isin(categories)

	q1 = frappe.qb.from_(ucf).select(fr.as_("n")).where(wc & fr.isnotnull() & (fr != ""))
	q2 = frappe.qb.from_(ucf).select(to.as_("n")).where(wc & to.isnotnull() & (to != ""))
	rows_raw = q1.union(q2).run(pluck=True)
	return {x for x in rows_raw if x}


def conversion_uoms_outside_categories(
	exclude_categories: list[str], limit_to: set[str]
) -> set[str]:
	if not limit_to:
		return set()

	ucf = frappe.qb.DocType("UOM Conversion Factor")
	fr, to = getattr(ucf, "from_uom"), getattr(ucf, "to_uom")
	q = frappe.qb.from_(ucf).select(fr, to).where(~ucf.category.isin(exclude_categories))

	out = set()
	for a, b in q.run(as_dict=False):
		if a in limit_to:
			out.add(a)
		if b in limit_to:
			out.add(b)
	return out


def transactional_uom_refs(cat_names: set[str]) -> set[str]:
	if not cat_names:
		return set()

	lnames = list(cat_names)
	out = set()
	for parent_dt, fieldname in collect_transactional_item_uom_link_branches():
		try:
			T = frappe.qb.DocType(parent_dt)
			col = getattr(T, fieldname)
		except AttributeError:
			continue
		q = frappe.qb.from_(T).select(col).distinct().where(col.isin(lnames))
		for v in q.run(pluck=True):
			if v:
				out.add(v)
	return out


def enforce_uom_curation_roles() -> None:
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles()) & {"System Manager", "Stock Manager", "Item Manager"}:
		frappe.throw(_("Insufficient permission for UOM category curation."), frappe.PermissionError)


@frappe.whitelist()
def get_uom_category_overview(category_name: str) -> dict[str, Any]:
	enforce_uom_curation_roles()
	frappe.has_permission("UOM", "write", throw=True)

	if not category_name or not frappe.db.exists("UOM Category", category_name):
		frappe.throw(_("UOM Category not found."), title=_("Invalid category"))

	cat_set = conversion_uoms_for_categories([category_name])
	if not cat_set:
		return {"rows": [], "category": category_name}

	txn_used = transactional_uom_refs(cat_set)
	refs_other_cat = conversion_uoms_outside_categories([category_name], cat_set)

	U = frappe.qb.DocType("UOM")
	masters = (
		frappe.qb.from_(U)
		.select(U.name, U.uom_name, U.enabled)
		.where(U.name.isin(list(cat_set)))
		.run(as_dict=True)
	)

	masters.sort(key=lambda r: ((r.uom_name or "").lower(), (r.name or "").lower()))

	rows = [
		{
			"uom": m.name,
			"uom_label": m.uom_name,
			"uom_enabled": m.enabled,
			"ref_other_uom_category": 1 if m.name in refs_other_cat else 0,
			"in_item_or_submittable": 1 if m.name in txn_used else 0,
		}
		for m in masters
	]
	return {"rows": rows, "category": category_name}


@frappe.whitelist()
def disable_unused_uoms_for_categories(categories) -> dict[str, Any]:
	enforce_uom_curation_roles()
	frappe.has_permission("UOM", "write", throw=True)

	validated = validated_categories_argument(categories)
	names_found = unused_uom_names(validated)
	if not names_found:
		return {"disabled": [], "count": 0, "categories": validated}

	to_disable = frappe.get_all(
		"UOM",
		filters={"name": ("in", names_found), "enabled": 1},
		pluck="name",
	)

	if not to_disable:
		return {"disabled": [], "count": 0, "categories": validated}

	U = frappe.qb.DocType("UOM")
	(frappe.qb.update(U).set(U.enabled, 0).where(U.name.isin(to_disable)).run())

	return {"disabled": to_disable, "count": len(to_disable), "categories": validated}


@frappe.whitelist()
def disable_unused_uoms_for_this_category(category_name: str) -> dict[str, Any]:
	if not category_name or not isinstance(category_name, str):
		frappe.throw(_("UOM Category name is required."))
	return disable_unused_uoms_for_categories([category_name])


@frappe.whitelist()
def enable_unused_uoms_for_categories(categories) -> dict[str, Any]:
	enforce_uom_curation_roles()
	frappe.has_permission("UOM", "write", throw=True)

	validated = validated_categories_argument(categories)
	names_found = unused_uom_names(validated)

	if not names_found:
		return {"enabled": [], "count": 0, "categories": validated}

	to_enable = frappe.get_all(
		"UOM",
		filters={"name": ("in", names_found), "enabled": 0},
		pluck="name",
	)
	if not to_enable:
		return {"enabled": [], "count": 0, "categories": validated}

	U = frappe.qb.DocType("UOM")
	(frappe.qb.update(U).set(U.enabled, 1).where(U.name.isin(to_enable)).run())

	return {"enabled": to_enable, "count": len(to_enable), "categories": validated}


@frappe.whitelist()
def enable_unused_uoms_for_this_category(category_name: str) -> dict[str, Any]:
	if not category_name or not isinstance(category_name, str):
		frappe.throw(_("UOM Category name is required."))
	return enable_unused_uoms_for_categories([category_name])
