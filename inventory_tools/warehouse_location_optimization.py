# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import math
from collections import defaultdict

import frappe
from frappe.query_builder import DocType
from frappe.utils import flt, getdate

from inventory_tools.cartonization import (
	get_physical_dimension,
	interior_physical_dimension_to_meter_normalized,
	resolve_item_physical_dimension,
	validate_2d_floor,
	validate_3d_volume,
)


def get_slotting_settings(company: str) -> frappe._dict:
	if frappe.db.exists("Inventory Tools Settings", company):
		return frappe.get_cached_doc("Inventory Tools Settings", company)
	return frappe._dict(
		require_plan_for_location_suggestion=1,
		location_suggestion_excluded_warehouse_types="Transit",
	)


def excluded_warehouse_types(settings) -> set[str]:
	raw = (settings.get("location_suggestion_excluded_warehouse_types") or "Transit").strip()
	if not raw:
		return set()
	return {part.strip() for part in raw.split(",") if part.strip()}


def resolve_scope(
	company: str, warehouse_plan: str, warehouse_branch: str | None = None
) -> set[str]:
	Wh = DocType("Warehouse")
	query = (
		frappe.qb.from_(Wh)
		.select(Wh.name)
		.where(Wh.company == company)
		.where(Wh.warehouse_plan == warehouse_plan)
	)

	if warehouse_branch:
		lft, rgt = frappe.db.get_value("Warehouse", warehouse_branch, ["lft", "rgt"])
		query = query.where((Wh.lft >= lft) & (Wh.rgt <= rgt))

	return set(query.run(pluck=True))


def compute_item_heat(
	scope: set[str],
	from_date,
	to_date,
	company: str,
) -> dict[str, dict]:
	if not scope:
		return {}

	SLE = DocType("Stock Ledger Entry")
	rows = (
		frappe.qb.from_(SLE)
		.select(
			SLE.item_code,
			SLE.voucher_type,
			SLE.voucher_no,
			SLE.actual_qty,
		)
		.where(SLE.company == company)
		.where(SLE.is_cancelled == 0)
		.where(SLE.posting_date >= getdate(from_date))
		.where(SLE.posting_date <= getdate(to_date))
		.where(SLE.warehouse.isin(list(scope)))
		.run(as_dict=True)
	)

	voucher_signs: dict[tuple, set[int]] = defaultdict(set)
	for row in rows:
		key = (row.item_code, row.voucher_type, row.voucher_no)
		sign = 1 if flt(row.actual_qty) > 0 else -1
		voucher_signs[key].add(sign)

	transfer_keys = {key for key, signs in voucher_signs.items() if 1 in signs and -1 in signs}

	item_heat: dict[str, dict] = defaultdict(lambda: {"count": 0, "qty": 0.0})
	counted_transfers: set[tuple] = set()

	for row in rows:
		item_code = row.item_code
		key = (item_code, row.voucher_type, row.voucher_no)
		qty = abs(flt(row.actual_qty))

		if key in transfer_keys:
			if key in counted_transfers:
				item_heat[item_code]["qty"] += qty
				continue
			counted_transfers.add(key)
			item_heat[item_code]["count"] += 1
		else:
			item_heat[item_code]["count"] += 1

		item_heat[item_code]["qty"] += qty

	return dict(item_heat)


def candidate_warehouses(
	warehouse_plan: str,
	scope: set[str],
	settings,
) -> list[dict]:
	if not scope:
		return []

	excluded_types = excluded_warehouse_types(settings)
	require_plan = settings.get("require_plan_for_location_suggestion", 1)

	filters = {
		"name": ["in", list(scope)],
		"is_group": 0,
		"disabled": 0,
	}
	if require_plan:
		filters["warehouse_plan"] = warehouse_plan
		filters["warehouse_plan_coordinates"] = ["is", "set"]

	warehouses = frappe.get_all(
		"Warehouse",
		filters=filters,
		fields=[
			"name",
			"warehouse_type",
			"warehouse_plan_coordinates",
			"accessible_path",
		],
	)

	out = []
	for wh in warehouses:
		if wh.warehouse_type and wh.warehouse_type in excluded_types:
			continue
		out.append(wh)

	return out


def warehouse_position(warehouse: dict) -> tuple[float, float] | None:
	if warehouse.get("accessible_path"):
		parts = [p.strip() for p in warehouse["accessible_path"].split(",") if p.strip()]
		if len(parts) >= 2:
			return float(parts[0]), float(parts[1])

	coords = warehouse.get("warehouse_plan_coordinates")
	if not coords:
		return None

	parts = [p.strip() for p in coords.split(",") if p.strip()]
	if len(parts) < 2:
		return None

	x = float(parts[0])
	y = float(parts[1])
	if len(parts) >= 4:
		width = float(parts[2])
		height = float(parts[3])
		return x + width / 2, y + height / 2

	return x, y


def plan_distance(
	warehouse: dict,
	pickup_x: float,
	pickup_y: float,
) -> float:
	position = warehouse_position(warehouse)
	if not position:
		return float("inf")

	dx = position[0] - pickup_x
	dy = position[1] - pickup_y
	return math.hypot(dx, dy)


def slot_dimension_payloads(item_code: str, warehouse: str):
	stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
	item_dim = resolve_item_physical_dimension(item_code, "Exterior", stock_uom)
	wh_dim = get_physical_dimension("Warehouse", warehouse, "Interior")

	if not item_dim or not wh_dim:
		return None

	item_normalized = interior_physical_dimension_to_meter_normalized(frappe._dict(item_dim))
	wh_normalized = interior_physical_dimension_to_meter_normalized(frappe._dict(wh_dim))

	item_length = flt(item_normalized.get("item_length"))
	item_width = flt(item_normalized.get("item_width"))
	item_height = flt(item_normalized.get("item_height"))
	wh_length = flt(wh_normalized.get("item_length"))
	wh_width = flt(wh_normalized.get("item_width"))
	wh_height = flt(wh_normalized.get("item_height"))

	if not all([item_length, item_width, wh_length, wh_width]):
		return None

	item_payload = {
		"item_length": item_length,
		"item_width": item_width,
		"item_height": item_height or 0,
		"item_volume": flt(item_normalized.get("item_volume"))
		or (item_length * item_width * (item_height or 0)),
		"qty": 1,
	}
	container_payload = {
		"item_length": wh_length,
		"item_width": wh_width,
		"item_height": wh_height or 0,
		"item_volume": flt(wh_normalized.get("item_volume"))
		or (wh_length * wh_width * (wh_height or 0)),
	}
	return item_dim, item_payload, container_payload, stock_uom


def item_fits_warehouse(item_code: str, warehouse: str) -> str:
	payloads = slot_dimension_payloads(item_code, warehouse)
	if not payloads:
		return "unverified"

	item_payload = payloads[1]
	container_payload = payloads[2]

	floor_result = validate_2d_floor([item_payload], container_payload)
	if not floor_result["fits"]:
		return "no_fit"

	if item_payload["item_height"] and container_payload["item_height"]:
		volume_result = validate_3d_volume([item_payload], container_payload)
		if not volume_result["fits"]:
			return "no_fit"

	return "fits"


def warehouse_slot_capacity(item_code: str, warehouse: str) -> float | None:
	"""How many units of this item (stock UOM) fit in the warehouse interior."""
	payloads = slot_dimension_payloads(item_code, warehouse)
	if not payloads:
		return None

	item_dim, item_payload, container_payload, stock_uom = payloads
	item_footprint = item_payload["item_length"] * item_payload["item_width"]
	container_area = container_payload["item_length"] * container_payload["item_width"]
	floor_capacity = math.floor(container_area / item_footprint) if item_footprint else 0

	if item_payload["item_height"] and container_payload["item_height"]:
		volume_capacity = (
			math.floor(container_payload["item_volume"] / item_payload["item_volume"])
			if item_payload["item_volume"]
			else floor_capacity
		)
		slot_capacity = min(floor_capacity, volume_capacity)
	else:
		slot_capacity = floor_capacity

	if slot_capacity <= 0:
		return None

	dimension_uom = item_dim.get("item_uom") or stock_uom
	if dimension_uom and stock_uom and dimension_uom != stock_uom:
		from erpnext.stock.get_item_details import get_conversion_factor

		conversion_factor = flt(
			get_conversion_factor(item_code, dimension_uom).get("conversion_factor") or 1
		)
		return float(slot_capacity * conversion_factor)

	return float(slot_capacity)


def suggest_putaway_rule_capacity(item_code: str, warehouse: str) -> float | None:
	return warehouse_slot_capacity(item_code, warehouse)


def resolve_putaway_rule_capacity(
	item_code: str,
	warehouse: str,
	capacity: float | None = None,
) -> float | None:
	if capacity is not None and flt(capacity) > 0:
		return flt(capacity)
	return warehouse_slot_capacity(item_code, warehouse)


def putaway_capacity_from_row(row, override_capacity: float | None = None) -> float | None:
	if override_capacity is not None and flt(override_capacity) > 0:
		return flt(override_capacity)
	row_capacity = row.get("capacity")
	if row_capacity not in (None, "") and flt(row_capacity) > 0:
		return flt(row_capacity)
	return resolve_putaway_rule_capacity(row.get("item_code"), row.get("suggested_warehouse"))


def parse_report_rows(rows):
	if isinstance(rows, str):
		rows = json.loads(rows)
	return rows or []


def warehouse_accessible_pos(warehouse: dict) -> tuple[int, int] | None:
	if warehouse.get("accessible_path"):
		parts = [p.strip() for p in warehouse["accessible_path"].split(",") if p.strip()]
		if len(parts) >= 2:
			return int(float(parts[0])), int(float(parts[1]))
	return None


def plan_walk_distance(warehouse: dict, context: dict) -> float:
	graph = context.get("plan_graph")
	position = warehouse_accessible_pos(warehouse)
	if graph and position:
		pickup = (int(context["pickup_x"]), int(context["pickup_y"]))
		start = graph.pos2node(pickup)
		end = graph.pos2node(position)
		if start in graph.G and end in graph.G:
			path, distance = graph.find_path(start, end)
			if distance:
				return float(distance)

	return plan_distance(warehouse, context["pickup_x"], context["pickup_y"])


def ordered_candidates_by_distance(candidates: list[dict], context: dict) -> list[dict]:
	return sorted(candidates, key=lambda candidate: plan_walk_distance(candidate, context))


def build_suggestion_context(plan, filters) -> dict:
	return {
		"company": filters.company,
		"warehouse_plan": filters.warehouse_plan,
		"pickup_x": float(plan.pickup_point_x),
		"pickup_y": float(plan.pickup_point_y),
		"from_date": filters.from_date,
		"to_date": filters.to_date,
		"plan_graph": plan.graph,
	}


def location_score(item_code: str, warehouse: dict, context: dict) -> float:
	score = plan_walk_distance(warehouse, context)

	for method_path in frappe.get_hooks("warehouse_location_score") or []:
		score = frappe.get_attr(method_path)(item_code, warehouse["name"], score, context)

	return score


def suggest_warehouse_by_heat_rank(
	item_code: str,
	candidates: list[dict],
	context: dict,
	slot_cursor: int,
) -> tuple[str | None, str, float | None, int]:
	"""Assign hotter items to nearer plan slots; each item claims the next fitting warehouse by walk distance."""
	ordered = context.get("ordered_candidates") or ordered_candidates_by_distance(candidates, context)
	if not ordered:
		return None, "no_fit", None, slot_cursor

	for step in range(len(ordered)):
		index = (slot_cursor + step) % len(ordered)
		candidate = ordered[index]
		fit_status = item_fits_warehouse(item_code, candidate["name"])
		if fit_status == "no_fit":
			continue

		score = location_score(item_code, candidate, context)
		return candidate["name"], fit_status, score, index + 1

	return None, "no_fit", None, slot_cursor


def get_putaway_rules_for_items(item_codes: list[str], company: str) -> dict[str, dict]:
	if not item_codes:
		return {}

	rules = frappe.get_all(
		"Putaway Rule",
		filters={
			"item_code": ["in", item_codes],
			"company": company,
			"disable": 0,
		},
		fields=["name", "item_code", "warehouse", "priority", "capacity"],
		order_by="priority asc",
	)

	out: dict[str, dict] = {}
	for rule in rules:
		if rule.item_code not in out:
			out[rule.item_code] = rule

	return out


def get_default_warehouses(item_codes: list[str], company: str) -> dict[str, str | None]:
	if not item_codes:
		return {}

	rows = frappe.get_all(
		"Item Default",
		filters={
			"parent": ["in", item_codes],
			"parenttype": "Item",
			"company": company,
		},
		fields=["parent", "default_warehouse"],
	)
	out = dict.fromkeys(item_codes)
	for row in rows:
		out[row.parent] = row.default_warehouse
	return out


def set_item_default_warehouse(item_code: str, warehouse: str, company: str) -> None:
	item = frappe.get_doc("Item", item_code)
	for row in item.item_defaults:
		if row.company == company:
			row.default_warehouse = warehouse
			item.save()
			return

	item.append("item_defaults", {"company": company, "default_warehouse": warehouse})
	item.save()


def set_putaway_rule_capacity(doc, capacity: float) -> None:
	"""Set capacity fields so Putaway Rule validation passes with stock on hand."""
	from erpnext.stock.get_item_details import get_conversion_factor
	from erpnext.stock.utils import get_stock_balance
	from frappe.utils import nowdate

	stock_uom = frappe.db.get_value("Item", doc.item_code, "stock_uom")
	if not doc.uom:
		doc.uom = stock_uom

	doc.conversion_factor = flt(
		get_conversion_factor(doc.item_code, doc.uom).get("conversion_factor") or 1
	)
	balance_qty = get_stock_balance(doc.item_code, doc.warehouse, nowdate())
	min_stock_capacity = flt(balance_qty) + 1
	requested_stock_capacity = flt(doc.conversion_factor) * flt(capacity)
	doc.stock_capacity = max(min_stock_capacity, requested_stock_capacity)
	doc.capacity = doc.stock_capacity / flt(doc.conversion_factor or 1)
