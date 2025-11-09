# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe


@frappe.whitelist()
def get_work_order_gantt_data(work_order=None, production_item=None):
	work_orders = get_work_order_dependencies(work_order, production_item)
	dependency_map = {}
	for d in work_orders:
		if d.dependent_on:
			if d.work_order not in dependency_map:
				dependency_map[d.work_order] = []
			dependency_map[d.work_order].append(d.dependent_on)
	return [
		{
			"id": wo.work_order,
			"name": f"{wo.production_item}:{wo.item_name}"
			if wo.item_name != wo.production_item
			else wo.production_item,
			"start": wo.planned_start_date,
			"end": wo.planned_end_date,
			"progress": 100 if wo.status == "Completed" else 10,
			"dependencies": ",".join(dependency_map.get(wo.work_order, [])),
		}
		for wo in work_orders
	]


def get_work_order_dependencies(work_order=None, production_item=None):
	conditions = ["wo.status = 'Not Started'"]
	if work_order:
		conditions.append(
			"""(
				wo.name = %(work_order)s
				OR wo2.name = %(work_order)s
				OR EXISTS (
					SELECT 1 FROM `tabWork Order Item` woi2
					WHERE woi2.parent = %(work_order)s
					AND woi2.item_code = wo.production_item
				)
		)"""
		)
	if production_item:
		conditions.append("wo.production_item = %(production_item)s")

	where_clause = "WHERE " + " AND ".join(conditions)

	query = f"""
	WITH RECURSIVE work_order_tree AS (
		SELECT
			wo.name as work_order,
			wo.production_item,
			wo.item_name,
			wo2.name as dependent_on,
			wo.planned_start_date,
			wo.planned_end_date,
			wo.status,
			0 as level
		FROM `tabWork Order` wo
		LEFT JOIN `tabWork Order Item` woi ON woi.parent = wo.name
		LEFT JOIN `tabWork Order` wo2 ON wo2.production_item = woi.item_code
		{where_clause}

		UNION ALL

		SELECT
			t.work_order,
			wo.production_item,
			wo.item_name,
			wo2.name,
			wo.planned_start_date,
			wo.planned_end_date,
			wo.status,
			t.level + 1
		FROM work_order_tree t
		JOIN `tabWork Order Item` woi ON woi.parent = t.dependent_on
		JOIN `tabWork Order` wo2 ON wo2.production_item = woi.item_code
		JOIN `tabWork Order` wo ON wo.name = t.work_order
		WHERE t.level < 10
	)
	SELECT * FROM work_order_tree
	GROUP BY work_order
	ORDER BY level
	"""
	return frappe.db.sql(
		query, {"work_order": work_order, "production_item": production_item}, as_dict=True
	)


def get_optimized_data(work_order_names=None, start_datetime=None):
	from Job_Shop_Scheduling_Benchmark_Environments_and_Instances.frappe.frappe_parser import FrappeJobShop
	op_schedule = FrappeJobShop(work_order_names)
	op_schedule.solve_fjsp()
	return op_schedule.get_optimizer_schedule(start_datetime)
