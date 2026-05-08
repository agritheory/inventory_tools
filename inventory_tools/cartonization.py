# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from erpnext.stock.get_item_details import get_conversion_factor
from frappe.utils import flt
from mip import BINARY, CONTINUOUS, Model, OptimizationStatus, xsum


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
	return resolve_item_physical_dimension(item_code, "Exterior")


def resolve_item_physical_dimension(item_code, dimension_type, line_uom=None):
	rows = frappe.get_all(
		"Physical Dimension",
		filters={
			"reference_doctype": "Item",
			"reference_document": item_code,
			"dimension_type": dimension_type,
		},
		fields=[
			"name",
			"item_length",
			"item_width",
			"item_height",
			"item_weight",
			"item_volume",
			"orientation",
			"uom",
			"item_uom",
		],
		order_by="name asc",
	)
	if not rows:
		return None
	if line_uom:
		exact_match = next((r for r in rows if r.get("item_uom") == line_uom), None)
		if exact_match:
			return frappe._dict(exact_match)

	stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
	if stock_uom:
		fallback_stock = next((r for r in rows if r.get("item_uom") == stock_uom), None)
		if fallback_stock:
			return frappe._dict(fallback_stock)

	return frappe._dict(rows[0])


def cartonization_row_qty_stock_uom(row_dict, item_code):
	for key in ("picked_qty", "stock_qty", "transfer_qty"):
		sq = flt(row_dict.get(key))
		if sq > 0:
			return sq

	line_qty = flt(row_dict.get("qty") or 0)
	if not line_qty:
		return 0.0

	stock_uom = row_dict.get("stock_uom") or frappe.db.get_value("Item", item_code, "stock_uom")
	line_uom = row_dict.get("uom") or stock_uom

	if line_uom == stock_uom:
		return line_qty

	return line_qty * float(get_conversion_factor(item_code, line_uom)["conversion_factor"] or 1)


def convert_stock_qty_to_physical_dimension_units(stock_qty, pd_item_uom, item_code):
	if not pd_item_uom or pd_item_uom == frappe.db.get_value("Item", item_code, "stock_uom"):
		return float(stock_qty)

	cf = float(get_conversion_factor(item_code, pd_item_uom)["conversion_factor"] or 1)
	if cf <= 0:
		return float(stock_qty)

	return float(stock_qty) / cf


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
	items: [{item_length, item_width, qty}]
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
	"""
	3D orthogonal bin-packing feasibility check using a MIP model (CBC solver).

	Each item unit becomes a box with position variables (x, y, z). Non-overlap
	between every pair is enforced via disjunctive big-M constraints. Optional
	L/W rotation is handled through a binary orientation variable per box.
	"""
	boxes = []
	for item in items:
		for _ in range(int(item["qty"])):
			boxes.append(
				{
					"item_code": item["item_code"],
					"l": float(item["item_length"]),
					"w": float(item["item_width"]),
					"h": float(item["item_height"]),
				}
			)

	if not boxes:
		return {"fits": True, "status": "NO_ITEMS"}

	CL = float(container["item_length"])
	CW = float(container["item_width"])
	CH = float(container["item_height"])
	n = len(boxes)

	model = Model(sense="MIN", solver_name="CBC")
	model.max_seconds = timeout
	model.verbose = 0

	x = [model.add_var(var_type=CONTINUOUS, lb=0, ub=CL) for _ in range(n)]
	y = [model.add_var(var_type=CONTINUOUS, lb=0, ub=CW) for _ in range(n)]
	z = [model.add_var(var_type=CONTINUOUS, lb=0, ub=CH) for _ in range(n)]

	if allow_rotation:
		# Binary variable: 0 = original orientation, 1 = swap L and W
		rot = [model.add_var(var_type=BINARY) for _ in range(n)]
		el = []
		ew = []
		for i, box in enumerate(boxes):
			l_i, w_i = box["l"], box["w"]
			# el[i] = l_i + (w_i - l_i)*rot[i]  (linear since rot is binary and coefficients constant)
			vi = model.add_var(var_type=CONTINUOUS, lb=min(l_i, w_i), ub=max(l_i, w_i))
			ui = model.add_var(var_type=CONTINUOUS, lb=min(l_i, w_i), ub=max(l_i, w_i))
			model += vi == l_i + (w_i - l_i) * rot[i]
			model += ui == w_i + (l_i - w_i) * rot[i]
			el.append(vi)
			ew.append(ui)
	else:
		el = [box["l"] for box in boxes]
		ew = [box["w"] for box in boxes]

	# Boundary constraints: each box must fit within container dimensions
	for i in range(n):
		model += x[i] + el[i] <= CL
		model += y[i] + ew[i] <= CW
		model += z[i] + boxes[i]["h"] <= CH

	# Non-overlap constraints via big-M disjunction for each pair (i, j):
	# At least one of 6 separations must hold
	M = max(CL, CW, CH)
	for i in range(n):
		for j in range(i + 1, n):
			sep = [model.add_var(var_type=BINARY) for _ in range(6)]
			model += xsum(sep) >= 1
			model += x[i] + el[i] <= x[j] + M * (1 - sep[0])  # i left of j
			model += x[j] + el[j] <= x[i] + M * (1 - sep[1])  # i right of j
			model += y[i] + ew[i] <= y[j] + M * (1 - sep[2])  # i in front of j
			model += y[j] + ew[j] <= y[i] + M * (1 - sep[3])  # i behind j
			model += z[i] + boxes[i]["h"] <= z[j] + M * (1 - sep[4])  # i below j
			model += z[j] + boxes[j]["h"] <= z[i] + M * (1 - sep[5])  # i above j

	status = model.optimize()

	return {
		"fits": status in (OptimizationStatus.OPTIMAL, OptimizationStatus.FEASIBLE),
		"status": status.name,
	}


def validate_weight(items, container):
	"""
	items: [{item_weight, qty}]
	container: {item_weight}  — item_weight on an Interior Physical Dimension is the max load capacity
	"""
	total_weight = sum((i.get("item_weight") or 0) * i["qty"] for i in items)
	max_weight = container.get("item_weight") or 0

	if not max_weight:
		return {"fits": True, "total_weight": total_weight, "max_weight": 0}

	return {
		"fits": total_weight <= max_weight,
		"total_weight": total_weight,
		"max_weight": max_weight,
		"utilization": total_weight / max_weight,
	}


def apply_policy(result, policy, context):
	if policy == "Ignore":
		return

	if result["fits"]:
		return

	message = f"Cartonization failed ({context}).\nDetails:\n{frappe.as_json(result, indent=2)}"

	if policy == "Warn":
		frappe.msgprint(message, indicator="orange", title="Cartonization Warning")

	elif policy == "Error":
		frappe.throw(message, title="Cartonization Error")


def get_item_rows(doc):
	"""
	Normalize item rows across doctypes.

	Returns a list of plain dict rows with:
	        item_code, qty (line UOM), warehouse, optional uom, stock_uom, conversion_factor,
	        and optional ERPNext-maintained qty-in-stock-uom helpers (picked_qty, stock_qty, transfer_qty).
	"""

	row_out = []

	if doc.doctype == "Pick List":
		for row in doc.locations:
			if row.item_code and row.warehouse:
				row_out.append(
					{
						"item_code": row.item_code,
						"qty": row.qty,
						"warehouse": row.warehouse,
						"uom": getattr(row, "uom", None),
						"stock_uom": getattr(row, "stock_uom", None),
						"conversion_factor": getattr(row, "conversion_factor", None),
						"picked_qty": getattr(row, "picked_qty", None),
						"stock_qty": getattr(row, "stock_qty", None),
					}
				)
		return row_out

	for row in doc.get("items") or []:
		if not row.item_code:
			continue
		row_out.append(
			{
				"item_code": row.item_code,
				"qty": row.qty,
				"warehouse": getattr(row, "warehouse", None)
				or getattr(row, "s_warehouse", None)
				or getattr(row, "t_warehouse", None),
				"uom": getattr(row, "uom", None),
				"stock_uom": getattr(row, "stock_uom", None),
				"conversion_factor": getattr(row, "conversion_factor", None),
				"transfer_qty": getattr(row, "transfer_qty", None),
			}
		)

	return row_out


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

		resolved_dimension = resolve_item_physical_dimension(
			row["item_code"], "Exterior", row.get("uom")
		)
		if not resolved_dimension:
			continue

		item_code = row["item_code"]

		physical_units = convert_stock_qty_to_physical_dimension_units(
			cartonization_row_qty_stock_uom(row, item_code),
			resolved_dimension["item_uom"],
			item_code,
		)

		dimension_row = frappe._dict(resolved_dimension)

		dimension_row.update({"qty": physical_units, "item_code": row["item_code"]})

		items_by_warehouse[row["warehouse"]].append(dimension_row)

	for warehouse, items in items_by_warehouse.items():
		container_dim, exempt = get_container_dimensions(warehouse=warehouse)

		if exempt or not container_dim:
			continue

		mode = settings["default_mode"]
		context = f"{doc.doctype} → Warehouse: {warehouse}"

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

		apply_policy(result, settings["policies"][mode], context)

		weight_result = validate_weight(items, container_dim)
		apply_policy(weight_result, settings["weight_policy"], f"{context} (weight)")
