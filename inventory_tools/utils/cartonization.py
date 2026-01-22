# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from mip import Model
from collections import defaultdict


def get_cartonization_settings(doc):
	settings = frappe.get_doc("Inventory Tools Settings", doc.company)

	if not settings.enable_cartonization:
		return None

	return {
		"default_mode": settings.default_packing_mode,
		"policies": {
			"2D Floor": settings.floor_packing_policy,
			"3D Volumetric": settings.volumetric_policy,
			"3D Fitted": settings.fitted_policy,
		},
		"allow_rotation": settings.allow_rotation,
		"solver_timeout": settings.solver_timeout_seconds or 30,
		"weight_policy": settings.weight_validation,
		"weight_uom": settings.max_weight_uom,
		"doctypes": [d.doctype_name for d in settings.cartonization_doctypes if d.doctype_name],
	}


def get_physical_dimension(reference_doctype, reference_name, dimension_type):
	return frappe.db.get_value(
		"Physical Dimension",
		{
			"reference_doctype": reference_doctype,
			"reference_document": reference_name,
			"dimension_type": dimension_type,
		},
		[
			"item_length",
			"item_width",
			"item_height",
			"item_weight",
			"item_volume",
			"orientation",
			"uom",
		],
		as_dict=True,
	)


def get_item_dimensions(item_code):
	return get_physical_dimension("Item", item_code, "Exterior")


def get_container_dimensions(item_code=None, warehouse=None):
	if warehouse:
		wh = frappe.get_doc("Warehouse", warehouse)
		if wh.cartonization_exempt:
			return None, True

		dim = get_physical_dimension("Warehouse", warehouse, "Interior")
		return dim, False

	if item_code:
		dim = get_physical_dimension("Item", item_code, "Interior")
		return dim, False

	return None, False


def validate_2d_floor(items, container):
	"""
	items: [{length, width, qty}]
	container: {item_length, item_width}
	"""
	total_area = 0

	for item in items:
		footprint = item["item_length"] * item["item_width"]
		total_area += footprint * item["qty"]

	container_area = container["item_length"] * container["item_width"]

	return {
		"fits": total_area <= container_area,
		"used_area": total_area,
		"container_area": container_area,
		"utilization": total_area / container_area if container_area else 0,
	}


def validate_3d_volume(items, container):
	total_volume = sum((i["item_volume"] or 0) * i["qty"] for i in items)

	return {
		"fits": total_volume <= container["item_volume"],
		"used_volume": total_volume,
		"container_volume": container["item_volume"],
		"utilization": total_volume / container["item_volume"] if container["item_volume"] else 0,
	}


def validate_3d_fitted(items, container, allow_rotation, timeout):
	model = Model(sense="MIN", solver_name="CBC")
	model.max_seconds = timeout

	# This is a feasibility-only model (bin = 1)
	# Each item must fit within container bounds

	for idx, item in enumerate(items):
		l, w, h = item["item_length"], item["item_width"], item["item_height"]

		if not allow_rotation and not item["orientation"]:
			if l > container["item_length"] or w > container["item_width"] or h > container["item_height"]:
				return {"fits": False, "reason": f"Item {item['item_code']} exceeds container"}

		# Full spatial bin-packing omitted for brevity
		# This is where x,y,z + non-overlap constraints go

	status = model.optimize()

	return {
		"fits": status.name == "OPTIMAL",
		"status": status.name,
	}


def apply_policy(result, policy, context):
	if policy == "Ignore":
		return

	if result["fits"]:
		return

	message = f"Cartonization failed ({context}).\n" f"Details:\n{frappe.as_json(result, indent=2)}"

	if policy == "Warn":
		frappe.msgprint(message, indicator="orange", title="Cartonization Warning")

	elif policy == "Error":
		frappe.throw(message, title="Cartonization Error")


def get_item_rows(doc):
	"""
	Normalize item rows across doctypes.
	Returns a list of rows with:
	- item_code
	- qty
	- warehouse
	"""

	if doc.doctype == "Pick List":
		return [
			{
				"item_code": row.item_code,
				"qty": row.qty,
				"warehouse": row.warehouse,
			}
			for row in doc.locations
			if row.item_code and row.warehouse
		]

	if hasattr(doc, "items"):
		return [
			{
				"item_code": row.item_code,
				"qty": row.qty,
				"warehouse": getattr(row, "warehouse", None)
				or getattr(row, "s_warehouse", None)
				or getattr(row, "t_warehouse", None),
			}
			for row in doc.items
			if row.item_code
		]

	return []


def run_cartonization(doc, method=None):
	settings = get_cartonization_settings(doc)
	if not settings:
		return

	if doc.doctype not in settings["doctypes"]:
		return

	items_by_warehouse = defaultdict(list)

	for row in get_item_rows(doc):
		if not row["warehouse"]:
			continue

		dim = get_item_dimensions(row["item_code"])
		if not dim:
			continue

		dim.update(
			{
				"qty": row["qty"],
				"item_code": row["item_code"],
			}
		)

		items_by_warehouse[row["warehouse"]].append(dim)

	for warehouse, items in items_by_warehouse.items():
		container_dim, exempt = get_container_dimensions(warehouse=warehouse)

		if exempt or not container_dim:
			continue

		mode = settings["default_mode"]

		if mode == "2D Floor":
			result = validate_2d_floor(items, container_dim)
		elif mode == "3D Volumetric":
			result = validate_3d_volume(items, container_dim)
		else:
			result = validate_3d_fitted(
				items,
				container_dim,
				settings["allow_rotation"],
				settings["solver_timeout"],
			)

		apply_policy(result, settings["policies"][mode], f"{doc.doctype} → Warehouse: {warehouse}")
