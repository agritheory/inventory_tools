# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate

from inventory_tools.warehouse_location_optimization import (
	build_suggestion_context,
	candidate_warehouses,
	compute_item_heat,
	get_default_warehouses,
	get_putaway_rules_for_items,
	get_slotting_settings,
	ordered_candidates_by_distance,
	parse_report_rows,
	putaway_capacity_from_row,
	resolve_scope,
	set_item_default_warehouse,
	set_putaway_rule_capacity,
	suggest_warehouse_by_heat_rank,
	warehouse_slot_capacity,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def validate_filters(filters):
	if not filters.get("company"):
		frappe.throw(frappe._("Company is required"))
	if not filters.get("warehouse_plan"):
		frappe.throw(frappe._("Warehouse Plan is required"))
	if not filters.get("from_date"):
		frappe.throw(frappe._("From Date is required"))
	if not filters.get("to_date"):
		frappe.throw(frappe._("To Date is required"))
	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(frappe._("From Date cannot be after To Date"))


def get_columns():
	return [
		{
			"label": "Item",
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 180,
		},
		{
			"label": "Heat",
			"fieldname": "heat",
			"fieldtype": "Int",
			"width": 80,
		},
		{
			"label": "Qty Moved",
			"fieldname": "qty_moved",
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"label": "Current Default Warehouse",
			"fieldname": "default_warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 180,
		},
		{
			"label": "Putaway Rule",
			"fieldname": "putaway_rule",
			"fieldtype": "Link",
			"options": "Putaway Rule",
			"width": 140,
		},
		{
			"label": "Putaway Warehouse",
			"fieldname": "putaway_warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 180,
		},
		{
			"label": "Suggested Warehouse",
			"fieldname": "suggested_warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 180,
		},
		{
			"label": "Slot Capacity",
			"fieldname": "capacity",
			"fieldtype": "Float",
			"width": 90,
			"description": "Units of this item (stock UOM) that fit in the suggested warehouse interior",
		},
		{
			"label": "Fit Status",
			"fieldname": "fit_status",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": "Score",
			"fieldname": "score",
			"fieldtype": "Float",
			"width": 90,
		},
		{
			"label": "Priority",
			"fieldname": "priority",
			"fieldtype": "Int",
			"width": 80,
		},
		{
			"fieldname": "heat_rank",
			"fieldtype": "Int",
			"hidden": 1,
		},
	]


def get_data(filters):
	settings = get_slotting_settings(filters.company)
	scope = resolve_scope(filters.company, filters.warehouse_plan, filters.get("warehouse"))
	heat_by_item = compute_item_heat(
		scope,
		filters.from_date,
		filters.to_date,
		filters.company,
	)

	if not heat_by_item:
		return []

	plan = frappe.get_cached_doc("Warehouse Plan", filters.warehouse_plan)
	candidates = candidate_warehouses(filters.warehouse_plan, scope, settings)
	context = build_suggestion_context(plan, filters)
	context["ordered_candidates"] = ordered_candidates_by_distance(candidates, context)

	ranked_items = sorted(
		((item_code, values) for item_code, values in heat_by_item.items() if values["count"] > 0),
		key=lambda row: (-row[1]["count"], -row[1]["qty"], row[0]),
	)

	item_codes = [item_code for item_code, _ in ranked_items]
	default_warehouses = get_default_warehouses(item_codes, filters.company)
	putaway_rules = get_putaway_rules_for_items(item_codes, filters.company)

	rows = []
	slot_cursor = 0
	for rank, (item_code, heat_values) in enumerate(ranked_items, start=1):
		suggested_warehouse, fit_status, score, slot_cursor = suggest_warehouse_by_heat_rank(
			item_code,
			candidates,
			context,
			slot_cursor,
		)
		putaway_rule = putaway_rules.get(item_code)
		capacity = (
			warehouse_slot_capacity(item_code, suggested_warehouse) if suggested_warehouse else None
		)

		rows.append(
			{
				"item_code": item_code,
				"heat": heat_values["count"],
				"qty_moved": heat_values["qty"],
				"default_warehouse": default_warehouses.get(item_code),
				"putaway_rule": putaway_rule.name if putaway_rule else None,
				"putaway_warehouse": putaway_rule.warehouse if putaway_rule else None,
				"suggested_warehouse": suggested_warehouse,
				"capacity": capacity,
				"fit_status": fit_status if suggested_warehouse else "no_fit",
				"score": score,
				"priority": rank,
				"heat_rank": rank,
			}
		)

	return rows


@frappe.whitelist()
def set_default_warehouses(rows, company=None):
	rows = parse_report_rows(rows)
	updated = []

	for row in rows:
		item_code = row.get("item_code")
		warehouse = row.get("suggested_warehouse")
		if not item_code or not warehouse:
			continue

		item_company = company or frappe.db.get_value("Warehouse", warehouse, "company")
		set_item_default_warehouse(item_code, warehouse, item_company)
		updated.append(item_code)

	return {"updated": updated}


@frappe.whitelist()
def create_putaway_rules(rows, capacity=None):
	rows = parse_report_rows(rows)
	override_capacity = flt(capacity) if capacity not in (None, "") else None
	if override_capacity is not None and override_capacity <= 0:
		frappe.throw(frappe._("Capacity must be greater than zero"))

	created = []
	updated = []

	for row in rows:
		item_code = row.get("item_code")
		warehouse = row.get("suggested_warehouse")
		priority = int(row.get("priority") or row.get("heat_rank") or 1)
		if not item_code or not warehouse:
			continue

		rule_capacity = putaway_capacity_from_row(row, override_capacity=override_capacity)
		if not rule_capacity:
			frappe.throw(
				frappe._(
					"Cannot create a putaway rule for {0} in {1}: slot capacity is unknown. Add item exterior and warehouse interior dimensions."
				).format(item_code, warehouse)
			)

		company = frappe.db.get_value("Warehouse", warehouse, "company")
		existing = frappe.db.get_value(
			"Putaway Rule",
			{"item_code": item_code, "warehouse": warehouse, "company": company},
			"name",
		)

		if existing:
			doc = frappe.get_doc("Putaway Rule", existing)
			doc.priority = priority
			doc.disable = 0
			set_putaway_rule_capacity(doc, rule_capacity)
			doc.save()
			updated.append(doc.name)
			continue

		doc = frappe.new_doc("Putaway Rule")
		doc.item_code = item_code
		doc.warehouse = warehouse
		doc.company = company
		doc.priority = priority
		set_putaway_rule_capacity(doc, rule_capacity)
		doc.insert()
		created.append(doc.name)

	return {"created": created, "updated": updated}
