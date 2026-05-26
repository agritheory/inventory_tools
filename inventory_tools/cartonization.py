# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

from __future__ import annotations

import math
from collections import defaultdict

import frappe
from erpnext.stock.doctype.item.item import get_uom_conv_factor
from erpnext.stock.get_item_details import get_conversion_factor
from frappe.utils import flt
from mip import BINARY, CONTINUOUS, Model, OptimizationStatus, xsum

BASE_LENGTH_UOM = "Meter"


def whole_units_that_fit(cap_measure: float, unit_measure: float) -> int:
	"""Discrete count such that ``count * unit_measure`` fits in ``cap_measure``.

	:class:`float` ratios like ``cap / unit`` can sit just below a whole number (three pie
	box volumes versus a cube carton with matching nominal dims). Prefer one more unit only
	when ``(n + 1) * unit <= cap`` within a tiny tolerance; otherwise ``floor(cap / unit)``.
	"""

	if unit_measure <= 0 or cap_measure <= 0:
		return 1
	cap_f = float(cap_measure)
	unit_f = float(unit_measure)
	ratio = cap_f / unit_f
	base = math.floor(ratio + 1e-15)
	next_n = base + 1
	# Stored L/W/H-derived volumes rarely match bit-for-bit across container vs item rows;
	# slack must exceed typical float gaps at exact nominal ratios (e.g. 12" cube / 12"×12"×4" pie trays).
	slack = max(unit_f * 1e-7, abs(cap_f) * 1e-9)
	if next_n * unit_f <= cap_f + slack:
		return max(1, next_n)
	return max(1, base)


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


# --- Multi-bin / ShipStation cartonization helpers -----------------------------------


def convert_length_quantity_to_meter(quantity: float, from_uom: str | None) -> float:
	"""Interpret ``quantity`` in ``from_uom`` and return Length in Meter."""
	q = flt(quantity)
	if q == 0:
		return 0.0
	if not from_uom or str(from_uom) == BASE_LENGTH_UOM:
		return float(q)

	factor_raw = get_uom_conv_factor(str(from_uom), BASE_LENGTH_UOM)
	try:
		factor = float(factor_raw or 0)
	except (TypeError, ValueError):
		factor = 0.0
	if not factor:
		frappe.throw(
			frappe._(
				"No UOM conversion from {0} to {1} for cartonization; add a global UOM Conversion Factor."
			).format(from_uom, BASE_LENGTH_UOM)
		)
	return q * factor


def interior_physical_dimension_to_meter_normalized(row: frappe._dict) -> frappe._dict:
	length_m = convert_length_quantity_to_meter(flt(row.get("item_length")), row.get("uom"))
	width_m = convert_length_quantity_to_meter(flt(row.get("item_width")), row.get("uom"))
	height_m = convert_length_quantity_to_meter(flt(row.get("item_height")), row.get("uom"))
	vol_m = length_m * width_m * height_m
	if vol_m <= 0 and row.get("item_volume"):
		uom_fac = convert_length_quantity_to_meter(1, row.get("uom"))
		scale = float(uom_fac**3 if uom_fac else 1.0)
		vol_m = flt(row.get("item_volume")) * scale

	return frappe._dict(
		{
			"name": row.get("name"),
			"item_length": length_m,
			"item_width": width_m,
			"item_height": height_m,
			"item_volume": vol_m,
			"item_weight_capacity": flt(row.get("item_weight") or 0),
			"reference_doctype": row.get("reference_doctype"),
			"reference_document": row.get("reference_document"),
			"uom": BASE_LENGTH_UOM,
		}
	)


def get_available_interior_containers(
	container_doctypes: list[str] | None,
) -> list[frappe._dict]:
	types = container_doctypes or ["Shipment Parcel Template", "Warehouse"]
	raw = frappe.get_all(
		"Physical Dimension",
		filters={"dimension_type": "Interior", "reference_doctype": ["in", types]},
		fields=[
			"name",
			"item_length",
			"item_width",
			"item_height",
			"item_volume",
			"item_weight",
			"uom",
			"reference_doctype",
			"reference_document",
		],
		order_by="reference_doctype asc, reference_document asc",
	)
	return [frappe._dict(c) for c in raw]


def build_carton_lines_from_plain_rows(rows: list[dict]) -> tuple[list[frappe._dict], list[str]]:
	"""Normalize plain item dicts into aggregate lines for bin packing."""
	lines: list[frappe._dict] = []
	messages: list[str] = []

	for row_dict in rows or []:
		item_code = row_dict.get("item_code")
		if not item_code:
			continue

		ext = resolve_item_physical_dimension(item_code, "Exterior", row_dict.get("uom"))
		if not ext:
			msg = frappe._(
				"Skipped {0}: add an Exterior Physical Dimension for this Item (stock-UOM-specific rows are optional)."
			).format(item_code)
			messages.append(str(msg))
			continue

		q_stock = cartonization_row_qty_stock_uom(row_dict, item_code)
		q_phys = convert_stock_qty_to_physical_dimension_units(q_stock, ext.get("item_uom"), item_code)
		if q_phys <= 0:
			continue

		length_m = convert_length_quantity_to_meter(flt(ext.item_length), ext.uom)
		width_m = convert_length_quantity_to_meter(flt(ext.item_width), ext.uom)
		height_m = convert_length_quantity_to_meter(flt(ext.item_height), ext.uom)
		v_piece = (
			length_m * width_m * height_m if length_m * width_m * height_m else flt(ext.item_volume or 0)
		)

		w_piece = flt(ext.item_weight or 0)
		total_v = float(v_piece * q_phys)
		total_w = float(w_piece * q_phys)

		lines.append(
			frappe._dict(
				{
					"item_code": item_code,
					"qty_line": flt(row_dict.get("qty") or row_dict.get("stock_qty")),
					"line_uom": row_dict.get("uom"),
					"stock_uom_for_row": row_dict.get("stock_uom"),
					"row_name": row_dict.get("name") or row_dict.get("row_name"),
					"dn_detail": row_dict.get("dn_detail"),
					"source_dimension_name": ext.get("name"),
					"physical_qty": float(q_phys),
					"volume_total_m3": total_v,
					"weight_total": total_w,
					"floor_area_total_m2": float(length_m * width_m * q_phys),
				}
			)
		)

	return lines, messages


def default_multi_bin_solver_settings(settings: dict | None) -> frappe._dict:
	base = frappe._dict(
		{
			"mode": "3D Volumetric",
			"allow_rotation": True,
			"solver_timeout": 30,
		}
	)
	if not settings:
		return base

	for key in ("mode", "default_mode"):
		if settings.get(key):
			base.mode = settings[key]

	if settings.get("allow_rotation") is not None:
		base.allow_rotation = bool(settings["allow_rotation"])

	if settings.get("solver_timeout"):
		base.solver_timeout = int(settings["solver_timeout"])

	return base


def volumetric_feasible(
	mode: str, used_v: float, used_wt: float, used_area: float, line: frappe._dict, cap: frappe._dict
) -> bool:
	cap_v = float(cap.item_volume or 0)
	cap_w = float(cap.item_weight_capacity or 0)
	cap_area = float((cap.item_length or 0) * (cap.item_width or 0))

	nv = used_v + float(line.volume_total_m3)
	nw = used_wt + float(line.weight_total)

	if mode == "2D Floor":
		na = used_area + float(line.floor_area_total_m2)
		if na > cap_area + 1e-9:
			return False
	else:
		if cap_v > 0 and nv > cap_v + 1e-9:
			return False

	if cap_w > 0 and nw > cap_w + 1e-9:
		return False

	return True


def split_line_into_container_chunks(
	line: frappe._dict, container: frappe._dict, mode: str
) -> list[frappe._dict]:
	"""Split ``line`` into sub-lines each containing at most as many units as fit in ``container``.

	Used when a row's total volume exceeds every available container but individual
	units still fit (e.g. 10 pies into a box that holds 3).  The per-unit footprint/
	volume/weight are preserved proportionally across all chunks.
	"""
	qty = float(line.physical_qty)
	if qty <= 0:
		return []

	unit_v = float(line.volume_total_m3) / qty
	unit_w = float(line.weight_total) / qty
	unit_area = float(line.floor_area_total_m2) / qty

	cap_v = float(container.item_volume or 0)
	cap_w = float(container.item_weight_capacity or 0)
	cap_area = float((container.item_length or 0) * (container.item_width or 0))

	max_by_v = whole_units_that_fit(cap_v, unit_v) if (unit_v > 0 and cap_v > 0) else int(qty)
	max_by_w = int(cap_w / unit_w + 1e-9) if (unit_w > 0 and cap_w > 0) else int(qty)

	if mode == "2D Floor":
		max_by_area = (
			whole_units_that_fit(cap_area, unit_area) if (unit_area > 0 and cap_area > 0) else int(qty)
		)
		chunk_size = max(1, min(max_by_v, max_by_w, max_by_area))
	else:
		chunk_size = max(1, min(max_by_v, max_by_w))

	chunks: list[frappe._dict] = []
	remaining = qty
	while remaining > 1e-9:
		n = min(chunk_size, remaining)
		chunks.append(
			frappe._dict(
				item_code=line.item_code,
				qty_line=float(line.qty_line or 0) * n / qty,
				line_uom=line.line_uom,
				stock_uom_for_row=line.stock_uom_for_row,
				row_name=line.row_name,
				dn_detail=line.dn_detail,
				source_dimension_name=line.source_dimension_name,
				physical_qty=n,
				volume_total_m3=unit_v * n,
				weight_total=unit_w * n,
				floor_area_total_m2=unit_area * n,
				_prepass_chunk=True,
				_prepass_chunk_size=chunk_size,
			)
		)
		remaining -= n
	return chunks


def smallest_container_that_fits_line(
	line: frappe._dict, normalized_containers: list[frappe._dict], mode: str
) -> frappe._dict | None:
	candidates = []
	for cap in normalized_containers:
		cap_area = float((cap.item_length or 0) * (cap.item_width or 0))

		if mode == "2D Floor":
			if line.floor_area_total_m2 <= cap_area + 1e-9 and (
				not cap.item_weight_capacity or line.weight_total <= cap.item_weight_capacity + 1e-9
			):
				candidates.append(cap)
			continue

		cap_v = float(cap.item_volume or 0)

		line_v = float(line.volume_total_m3)
		if cap_v > 0:
			ok_volume = line_v <= cap_v + 1e-9
		else:
			ok_volume = True
		ok_weight = True
		if cap.item_weight_capacity:
			ok_weight = line.weight_total <= cap.item_weight_capacity + 1e-9

		if ok_volume and ok_weight:
			candidates.append(cap)

	candidates.sort(key=lambda c: float(c.item_volume or 0))

	return candidates[0] if candidates else None


def best_chunk_container(
	unit_line: frappe._dict, normalized_containers: list[frappe._dict], mode: str
) -> frappe._dict | None:
	"""Pick the parcel interior used to chunk an oversized carton line during the pre-pass.

	Among containers that can hold at least one unit, evaluate discrete whole-unit fill
	(utilization) on volume or floor footprint. If the pool also offers a carton that holds
	two or more units, single-unit-only options (``cs == 1``) are dropped — they often win
	utilization by a negligible margin over much larger cartons and explode parcel count.

	The winner maximizes ``(utilization, -interior measure, units per chunk)`` so a
	purpose-sized interior with the same nominal utilization as a loose medium carton is
	preferred, and near-100 percent fill still wins over lower utilization.
	"""
	unit_v = float(unit_line.volume_total_m3)
	unit_w = float(unit_line.weight_total)
	unit_area = float(unit_line.floor_area_total_m2)

	rows: list[dict] = []
	for cap in normalized_containers:
		if mode == "2D Floor":
			cap_area = float((cap.item_length or 0) * (cap.item_width or 0))
			fit_slack = max(unit_area * 1e-7, cap_area * 1e-9)
			if unit_area > cap_area + fit_slack:
				continue
			ok_weight = not cap.item_weight_capacity or unit_w <= cap.item_weight_capacity + 1e-9
			if not ok_weight:
				continue
			cs = max(1, whole_units_that_fit(cap_area, unit_area)) if unit_area > 0 else 1
			util = min(1.0, (cs * unit_area) / cap_area) if cap_area > 1e-30 and unit_area > 1e-30 else 0.0
			rows.append({"cap": cap, "util": util, "cs": cs, "cap_m": cap_area})
		else:
			cap_v = float(cap.item_volume or 0)
			fit_slack = max(unit_v * 1e-7, cap_v * 1e-9)
			if cap_v <= 0 or unit_v > cap_v + fit_slack:
				continue
			ok_weight = not cap.item_weight_capacity or unit_w <= cap.item_weight_capacity + 1e-9
			if not ok_weight:
				continue
			cs_v = max(1, whole_units_that_fit(cap_v, unit_v)) if unit_v > 0 else 1
			cap_w = float(cap.item_weight_capacity or 0)
			cs_w = max(1, int(cap_w / unit_w + 1e-9)) if (unit_w > 0 and cap_w > 0) else cs_v
			cs = min(cs_v, cs_w)
			util = min(1.0, (cs * unit_v) / cap_v) if unit_v > 1e-30 else 1.0
			rows.append({"cap": cap, "util": util, "cs": cs, "cap_m": cap_v})

	if not rows:
		return None

	max_cs = max(int(r["cs"]) for r in rows)
	if max_cs > 1:
		filtered = [r for r in rows if int(r["cs"]) > 1]
		if filtered:
			rows = filtered

	best = max(rows, key=lambda r: (float(r["util"]), -float(r["cap_m"]), int(r["cs"])))
	return best["cap"]


def apply_3d_fitted_check_for_bin(
	bin_lines: list[frappe._dict], cap: frappe._dict, solver_settings: frappe._dict
) -> dict:
	items_for_fit = []
	for ln in bin_lines:
		ext = frappe.get_cached_doc("Physical Dimension", ln.source_dimension_name)
		length_m = convert_length_quantity_to_meter(flt(ext.item_length), ext.uom)
		width_m = convert_length_quantity_to_meter(flt(ext.item_width), ext.uom)
		height_m = convert_length_quantity_to_meter(flt(ext.item_height), ext.uom)
		q_phys = ln.physical_qty

		if abs(q_phys - int(q_phys)) > 1e-6:
			return {"fits": True, "status": "FRACTIONAL_QTY_FALLBACK"}

		box = {
			"item_length": length_m,
			"item_width": width_m,
			"item_height": height_m,
			"item_volume": length_m * width_m * height_m,
			"item_weight": flt(ext.item_weight or 0),
			"item_code": ln.item_code,
			"qty": int(round(q_phys)),
		}
		items_for_fit.append(box)

	container_for_fit = frappe._dict(
		{
			"item_length": cap.item_length,
			"item_width": cap.item_width,
			"item_height": cap.item_height,
			"item_volume": cap.item_volume,
			"item_weight": cap.item_weight_capacity or 0,
		}
	)

	return validate_3d_fitted(
		items_for_fit,
		container_for_fit,
		solver_settings.allow_rotation,
		solver_settings.solver_timeout,
	)


def solve_cartonization(
	items: list[dict],
	container_doctypes: list[str] | None = None,
	company: str | None = None,
	settings: dict | None = None,
	reference_document_filters: dict | None = None,
) -> frappe._dict:
	"""Heuristic multi-bin packer aligned with Exterior/Interior Physical Dimensions."""

	solver_settings = default_multi_bin_solver_settings(settings)

	raw_containers = get_available_interior_containers(container_doctypes)
	if reference_document_filters:
		filtered = []
		for c in raw_containers:
			allowed_for_type = reference_document_filters.get(c.reference_doctype)
			if allowed_for_type and c.reference_document not in allowed_for_type:
				continue
			filtered.append(c)
		raw_containers = filtered

	normalized_containers = [
		interior_physical_dimension_to_meter_normalized(c) for c in raw_containers
	]

	if not normalized_containers:
		return frappe._dict(
			bins=[],
			skipped=items or [],
			messages=[
				str(
					frappe._("No Interior Physical Dimensions found for requested container reference doctypes.")
				)
			],
			warnings=[],
		)

	lines, msgs = build_carton_lines_from_plain_rows(items)

	if not lines:
		return frappe._dict(bins=[], skipped=items or [], messages=msgs, warnings=msgs)

	mode = solver_settings.mode or "3D Volumetric"

	# Pre-pass: split any line whose total volume exceeds every container into per-
	# capacity chunks (e.g. 10 pies where the container holds 3 → chunks of 3,3,3,1).
	# A line with physical_qty == 1 that still doesn't fit will be caught in the main
	# loop and reported as skipped.
	expanded_lines: list[frappe._dict] = []
	for line in lines:
		if smallest_container_that_fits_line(line, normalized_containers, mode):
			expanded_lines.append(line)
		elif float(line.physical_qty) > 1:
			unit = frappe._dict(
				**{
					**line,
					"physical_qty": 1.0,
					"volume_total_m3": float(line.volume_total_m3) / float(line.physical_qty),
					"weight_total": float(line.weight_total) / float(line.physical_qty),
					"floor_area_total_m2": float(line.floor_area_total_m2) / float(line.physical_qty),
					"qty_line": float(line.qty_line or 0) / float(line.physical_qty),
				}
			)
			cap_for_unit = best_chunk_container(unit, normalized_containers, mode)
			if cap_for_unit:
				expanded_lines.extend(split_line_into_container_chunks(line, cap_for_unit, mode))
			else:
				expanded_lines.append(line)
		else:
			expanded_lines.append(line)
	lines = expanded_lines

	sort_key_fn = (
		lambda ln: ln.floor_area_total_m2 if mode == "2D Floor" else ln.volume_total_m3
	)  # noqa
	sorted_lines = sorted(lines, key=sort_key_fn, reverse=True)

	bins_open: list[dict] = []
	skipped_remaining: list[frappe._dict] = []

	for line in sorted_lines:
		placed = False
		for b in bins_open:
			cap = b["capacity"]
			if volumetric_feasible(
				mode,
				b["vol_used"],
				b["wt_used"],
				b["area_used"],
				line,
				cap,
			):
				if solver_settings.mode == "3D Fitted":
					trial_lines = [*b["lines"], line]
					fit_chk = apply_3d_fitted_check_for_bin(trial_lines, cap, solver_settings)
					if not fit_chk.get("fits"):
						continue

				b["lines"].append(line)
				b["vol_used"] += float(line.volume_total_m3)
				b["wt_used"] += float(line.weight_total)
				b["area_used"] += float(line.floor_area_total_m2)
				placed = True
				break

		if placed:
			continue

		# Pre-pass chunks reuse the best-chunk strategy so remainder chunks can
		# consolidate across item types (e.g. two 1-pie remainders sharing one
		# Pie Triple Stack bin instead of each opening a separate Small Box).
		if line.get("_prepass_chunk"):
			cap0 = best_chunk_container(line, normalized_containers, mode)
		else:
			cap0 = smallest_container_that_fits_line(line, normalized_containers, mode)
		if not cap0:
			skipped_remaining.append(line)
			msgs.append(
				str(frappe._("No container could fit remaining volume for Item {0}.").format(line.item_code))
			)
			continue

		if solver_settings.mode == "3D Fitted":
			fit_chk = apply_3d_fitted_check_for_bin([line], cap0, solver_settings)
			if not fit_chk.get("fits"):
				skipped_remaining.append(line)
				msgs.append(
					str(
						frappe._("Item {0} failed 3D fitted check for smallest container candidate.").format(
							line.item_code
						)
					)
				)
				continue

		bins_open.append(
			{
				"capacity": cap0,
				"lines": [line],
				"vol_used": float(line.volume_total_m3),
				"wt_used": float(line.weight_total),
				"area_used": float(line.floor_area_total_m2),
			}
		)

	result_bins = []
	warnings_for_call = [*msgs]

	for idx, bin_data in enumerate(bins_open, start=1):
		cap = bin_data["capacity"]
		cap_v = float(cap.item_volume or 0)
		util = (bin_data["vol_used"] / cap_v) if cap_v else 0.0

		packed_lines = []
		for ln in bin_data["lines"]:
			packed_lines.append(
				{
					"item_code": ln.item_code,
					"qty": ln.qty_line,
					"uom": ln.line_uom,
					"row_name": ln.row_name,
					"dn_detail": ln.dn_detail,
					"source_dimension_name": ln.source_dimension_name,
					"volume_total_m3": ln.volume_total_m3,
					"weight_total": ln.weight_total,
				}
			)

		cap_area = float((cap.item_length or 0) * (cap.item_width or 1)) or 1e-9
		area_util = bin_data["area_used"] / cap_area if mode == "2D Floor" else util

		result_bins.append(
			frappe._dict(
				bin_number=idx,
				container_dimension=cap.name,
				container=dict(
					doctype=cap.reference_doctype,
					name=cap.reference_document,
				),
				items=packed_lines,
				utilization=area_util if mode == "2D Floor" else util,
				total_weight=bin_data["wt_used"],
				company=company,
				parcel_template=cap.reference_document
				if cap.reference_doctype == "Shipment Parcel Template"
				else None,
			)
		)

	return frappe._dict(
		bins=result_bins,
		skipped=[dict(x) for x in skipped_remaining],
		messages=[str(m) for m in msgs],
		warnings=[str(w) for w in warnings_for_call],
	)


CACHE_KEY_PREFIX = "best_fit_containers:"


def get_best_fit_containers(
	item_code: str,
	uom: str | None,
	container_doctypes: list[str],
	company: str | None = None,
	limit: int = 5,
	compute_if_missing: bool = True,
) -> list[dict]:
	"""Return ranked container targets for a single item + UOM using fits + solver hints."""

	types_key = "|".join(sorted(container_doctypes or []))
	cc = company or ""
	cache_key = f"{CACHE_KEY_PREFIX}{item_code}:{uom or ''}:{cc}:{types_key}"
	cached = frappe.cache.get_value(cache_key)
	if cached is not None:
		return cached[:limit]

	ext = resolve_item_physical_dimension(item_code, "Exterior", uom)
	if not ext or not ext.get("name"):
		return []

	ext_name = ext.name

	fit_rows = frappe.get_all(
		"Physical Dimension Fit",
		filters={"source_dimension": ext_name},
		fields=[
			"name",
			"target_dimension",
			"fit_score",
			"fit_method",
			"rank",
			"company",
		],
		order_by="rank asc",
		limit_page_length=min(limit * 8, 400),
	)

	def company_ok(row_company: str | None) -> bool:
		if company:
			return not row_company or row_company == company
		return not row_company

	out: list[dict] = []
	for row in fit_rows:
		if not company_ok(row.company):
			continue

		td = frappe.get_cached_value(
			"Physical Dimension",
			row.target_dimension,
			["reference_doctype", "reference_document"],
			as_dict=True,
		)

		if container_doctypes and td.reference_doctype not in container_doctypes:
			continue

		out.append(
			{
				"physical_dimension_fit": row.name,
				"target_dimension_name": row.target_dimension,
				"container_doctype": td.reference_doctype,
				"container_name": td.reference_document,
				"fit_score": row.fit_score,
				"rank": row.rank,
				"from_record": True,
			}
		)

	if len(out) >= limit:
		frappe.cache.set_value(cache_key, out[:limit], expires_in_sec=3600)
		return out[:limit]

	if not compute_if_missing:
		frappe.cache.set_value(cache_key, out[:limit], expires_in_sec=3600)
		return out[:limit]

	sample_line = {
		"item_code": item_code,
		"qty": 1,
		"uom": uom,
		"name": "__best_fit_probe__",
	}
	solution = solve_cartonization(
		[sample_line], container_doctypes=container_doctypes, company=company
	)

	seen = {(e["container_doctype"], e["container_name"]): e for e in out}

	for bn in solution.get("bins", []):
		cdim = frappe.get_cached_value(
			"Physical Dimension",
			bn.container_dimension,
			["reference_doctype", "reference_document"],
			as_dict=True,
		)

		if container_doctypes and cdim.reference_doctype not in container_doctypes:
			continue

		key = (cdim.reference_doctype, cdim.reference_document)
		if key in seen:
			continue

		cap = interior_physical_dimension_to_meter_normalized(
			frappe.get_cached_doc("Physical Dimension", bn.container_dimension)
		)

		score_hint = bn.utilization
		if score_hint <= 0 or score_hint > 1:
			score_hint = min(1.0, bn.utilization) if bn.utilization >= 0 else 0.0

		new_entry = {
			"physical_dimension_fit": None,
			"target_dimension_name": bn.container_dimension,
			"container_doctype": cdim.reference_doctype,
			"container_name": cdim.reference_document,
			"fit_score": score_hint,
			"rank": len(seen) + 1,
			"from_record": False,
		}

		out.append(new_entry)
		seen[key] = new_entry

	out_sorted = sorted(
		out,
		key=lambda row: (-flt(row.get("fit_score") or 0), int(row.get("rank") or 999)),
	)

	frappe.cache.set_value(cache_key, out_sorted[:limit], expires_in_sec=3600)

	return out_sorted[:limit]


def get_available_containers(
	container_doctypes: list[str] | None,
	company: str | None = None,
) -> list[frappe._dict]:
	"""Interior ``Physical Dimension`` rows filtered by container ``reference_doctype``.

	Optional ``company`` is accepted for API compatibility; filtering is not implemented yet.
	"""
	return get_available_interior_containers(container_doctypes)
