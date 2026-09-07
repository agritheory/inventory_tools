# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import timeit
from typing import Any

import frappe
from erpnext.stock.doctype.uom_category.uom_category import UOMCategory
from frappe import _
from frappe.model.meta import get_parent_dt
from frappe.model.rename_doc import get_link_fields
from frappe.query_builder.functions import Count


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


def empty_usage_counts(cat_names: set[str]) -> dict[str, dict[str, Any]]:
	return {uom: {"total": 0, "by_doctype": {}} for uom in cat_names}


def scan_transactional_uom_usage(
	cat_names: set[str],
	*,
	category_name: str,
	phase: str = "scan",
) -> dict[str, dict[str, Any]]:
	if not cat_names:
		return {}

	lnames = list(cat_names)
	branches = collect_transactional_item_uom_link_branches()
	total = len(branches)
	usage = empty_usage_counts(cat_names)
	last_eta = 0.0

	for idx, (parent_dt, fieldname) in enumerate(branches, start=1):
		start = timeit.default_timer()
		branch_key = f"{parent_dt}.{fieldname}"
		try:
			T = frappe.qb.DocType(parent_dt)
			col = getattr(T, fieldname)
		except AttributeError:
			processing_time = timeit.default_timer() - start
			last_eta = update_scan_eta(last_eta, idx, total, processing_time)
			publish_uom_curation_progress(category_name, phase, idx, total, last_eta)
			continue

		q = frappe.qb.from_(T).select(col, Count("*").as_("n")).where(col.isin(lnames)).groupby(col)
		for uom, count in q.run(as_dict=False):
			if not uom or uom not in usage:
				continue
			row_count = int(count)
			if row_count <= 0:
				continue
			usage[uom]["total"] += row_count
			usage[uom]["by_doctype"][branch_key] = row_count

		processing_time = timeit.default_timer() - start
		last_eta = update_scan_eta(last_eta, idx, total, processing_time)
		publish_uom_curation_progress(category_name, phase, idx, total, last_eta)

	return usage


def update_scan_eta(last_eta: float, current: int, total: int, processing_time: float) -> float:
	remaining = total - current
	eta = processing_time * remaining
	if not last_eta or eta < last_eta:
		return eta
	return last_eta


def publish_uom_curation_progress(
	category_name: str,
	phase: str,
	current: int,
	total: int,
	eta: float,
	**extra: Any,
) -> None:
	payload = {
		"category": category_name,
		"phase": phase,
		"current": current,
		"total": total,
		"eta": eta,
		**extra,
	}
	frappe.publish_realtime("uom_curation_progress", payload, user=frappe.session.user)


def unused_uom_names(
	validated_categories: list[str],
	usage_counts: dict[str, dict[str, Any]],
) -> list[str]:
	cat_names = conversion_uoms_for_categories(validated_categories)
	cross_used = conversion_uoms_outside_categories(validated_categories, cat_names)
	unused = []
	for uom in sorted(cat_names):
		if uom in cross_used:
			continue
		if usage_counts.get(uom, {}).get("total", 0) > 0:
			continue
		unused.append(uom)
	return unused


def build_overview_rows(
	category_name: str,
	usage_counts: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
	cat_set = set(usage_counts.keys()) or conversion_uoms_for_categories([category_name])
	if not cat_set:
		return []

	refs_other_cat = conversion_uoms_outside_categories([category_name], cat_set)

	U = frappe.qb.DocType("UOM")
	masters = (
		frappe.qb.from_(U)
		.select(U.name, U.uom_name, U.enabled)
		.where(U.name.isin(list(cat_set)))
		.run(as_dict=True)
	)

	masters.sort(key=lambda r: ((r.uom_name or "").lower(), (r.name or "").lower()))

	rows = []
	for master in masters:
		counts = usage_counts.get(master.name, {"total": 0, "by_doctype": {}})
		rows.append(
			{
				"uom": master.name,
				"uom_label": master.uom_name,
				"uom_enabled": master.enabled,
				"ref_other_uom_category": 1 if master.name in refs_other_cat else 0,
				"transactional_usage_count": counts.get("total", 0),
				"transactional_usage_by_doctype": counts.get("by_doctype", {}),
			}
		)
	return rows


def cache_uom_category_overview(category_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
	payload = {
		"rows": rows,
		"category": category_name,
		"scanned_at": frappe.utils.now(),
	}
	frappe.cache.set_value(
		f"uom_curation_scan:{category_name}",
		payload,
		expires_in_sec=86400,
	)
	return payload


def get_cached_uom_category_overview_payload(category_name: str) -> dict[str, Any] | None:
	return frappe.cache.get_value(f"uom_curation_scan:{category_name}")


def clear_uom_category_overview_cache(category_name: str) -> None:
	frappe.cache.delete_value(f"uom_curation_scan:{category_name}")


def enforce_uom_curation_roles() -> None:
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles()) & {"System Manager", "Stock Manager", "Item Manager"}:
		frappe.throw(_("Insufficient permission for UOM category curation."), frappe.PermissionError)


def validate_uom_curation_access(category_name: str) -> None:
	enforce_uom_curation_roles()
	frappe.has_permission("UOM", "write", throw=True)
	if not category_name or not frappe.db.exists("UOM Category", category_name):
		frappe.throw(_("UOM Category not found."), title=_("Invalid category"))


def enqueue_uom_curation_doc_method(doc, method: str) -> None:
	if frappe.flags.in_test:
		getattr(doc, method)()
		return

	frappe.enqueue_doc(
		doc.doctype,
		doc.name,
		method,
		queue="long",
		timeout=3600,
	)


@frappe.whitelist()
def get_cached_uom_category_overview(category_name: str) -> dict[str, Any]:
	validate_uom_curation_access(category_name)
	cached = get_cached_uom_category_overview_payload(category_name)
	if cached:
		return cached
	return {"rows": [], "category": category_name}


class InventoryToolsUOMCategory(UOMCategory):
	@frappe.whitelist()
	def start_uom_usage_scan(self) -> dict[str, Any]:
		validate_uom_curation_access(self.name)
		clear_uom_category_overview_cache(self.name)
		enqueue_uom_curation_doc_method(self, "run_uom_usage_scan")
		return {"queued": True, "category": self.name}

	def run_uom_usage_scan(self) -> None:
		cat_set = conversion_uoms_for_categories([self.name])
		if not cat_set:
			payload = cache_uom_category_overview(self.name, [])
			publish_uom_curation_progress(
				self.name,
				"scan",
				0,
				0,
				0,
				rows=payload["rows"],
				complete=1,
			)
			return

		usage_counts = scan_transactional_uom_usage(
			cat_set,
			category_name=self.name,
			phase="scan",
		)
		rows = build_overview_rows(self.name, usage_counts)
		payload = cache_uom_category_overview(self.name, rows)
		branches = collect_transactional_item_uom_link_branches()
		publish_uom_curation_progress(
			self.name,
			"scan",
			len(branches),
			len(branches),
			0,
			rows=payload["rows"],
			complete=1,
		)
		frappe.db.commit()  # nosemgrep: frappe-manual-commit — persist before realtime complete

	@frappe.whitelist()
	def start_disable_unused_uoms(self) -> dict[str, Any]:
		validate_uom_curation_access(self.name)
		clear_uom_category_overview_cache(self.name)
		enqueue_uom_curation_doc_method(self, "run_disable_unused_uoms")
		return {"queued": True, "category": self.name}

	def run_disable_unused_uoms(self) -> None:
		cat_set = conversion_uoms_for_categories([self.name])
		if not cat_set:
			publish_uom_curation_progress(
				self.name,
				"disable",
				0,
				0,
				0,
				disabled=[],
				count=0,
				complete=1,
			)
			return

		usage_counts = scan_transactional_uom_usage(
			cat_set,
			category_name=self.name,
			phase="disable",
		)
		names_found = unused_uom_names([self.name], usage_counts)
		to_disable = []
		if names_found:
			to_disable = frappe.get_all(
				"UOM",
				filters={"name": ("in", names_found), "enabled": 1},
				pluck="name",
			)
			if to_disable:
				U = frappe.qb.DocType("UOM")
				(frappe.qb.update(U).set(U.enabled, 0).where(U.name.isin(to_disable)).run())

		rows = build_overview_rows(self.name, usage_counts)
		payload = cache_uom_category_overview(self.name, rows)
		branches = collect_transactional_item_uom_link_branches()
		publish_uom_curation_progress(
			self.name,
			"disable",
			len(branches),
			len(branches),
			0,
			rows=payload["rows"],
			disabled=to_disable,
			count=len(to_disable),
			complete=1,
		)
		frappe.db.commit()  # nosemgrep: frappe-manual-commit — persist before realtime complete

	@frappe.whitelist()
	def start_enable_unused_uoms(self) -> dict[str, Any]:
		validate_uom_curation_access(self.name)
		clear_uom_category_overview_cache(self.name)
		enqueue_uom_curation_doc_method(self, "run_enable_unused_uoms")
		return {"queued": True, "category": self.name}

	def run_enable_unused_uoms(self) -> None:
		cat_set = conversion_uoms_for_categories([self.name])
		if not cat_set:
			publish_uom_curation_progress(
				self.name,
				"enable",
				0,
				0,
				0,
				enabled=[],
				count=0,
				complete=1,
			)
			return

		usage_counts = scan_transactional_uom_usage(
			cat_set,
			category_name=self.name,
			phase="enable",
		)
		names_found = unused_uom_names([self.name], usage_counts)
		to_enable = []
		if names_found:
			to_enable = frappe.get_all(
				"UOM",
				filters={"name": ("in", names_found), "enabled": 0},
				pluck="name",
			)
			if to_enable:
				U = frappe.qb.DocType("UOM")
				(frappe.qb.update(U).set(U.enabled, 1).where(U.name.isin(to_enable)).run())

		rows = build_overview_rows(self.name, usage_counts)
		payload = cache_uom_category_overview(self.name, rows)
		branches = collect_transactional_item_uom_link_branches()
		publish_uom_curation_progress(
			self.name,
			"enable",
			len(branches),
			len(branches),
			0,
			rows=payload["rows"],
			enabled=to_enable,
			count=len(to_enable),
			complete=1,
		)
		frappe.db.commit()  # nosemgrep: frappe-manual-commit — persist before realtime complete
