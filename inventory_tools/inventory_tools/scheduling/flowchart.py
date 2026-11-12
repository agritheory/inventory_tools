# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import json

import frappe
from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import (
	get_mins_between_operations,
)
from frappe import _
from frappe.utils import add_to_date, flt, get_datetime, time_diff_in_seconds

from inventory_tools.inventory_tools.scheduling.precedence import (
	RELATION_ABBREVIATIONS,
	TOLERANCE,
	Issue,
	OperationNode,
	binding_edges,
	build_operation_graph,
	compute_time_windows,
	normalize_sequence_ids,
)

FLOWCHART_DOCTYPES = ("BOM", "Routing", "Work Order")


@frappe.whitelist()
def get_operation_flowchart(doctype: str, name: str | None = None, doc: str | None = None) -> dict:
	"""Nodes, edges, time windows, and issues for the operations of a Routing,
	BOM, or Work Order. Pass `doc` (JSON) to chart unsaved changes."""
	if doctype not in FLOWCHART_DOCTYPES:
		frappe.throw(
			_("Operation flowcharts are available for {0}").format(", ".join(FLOWCHART_DOCTYPES))
		)

	if doc:
		document = frappe.get_doc(json.loads(doc) if isinstance(doc, str) else doc)
		if document.doctype != doctype:
			frappe.throw(_("Document type does not match"))
		if document.get("name") and frappe.db.exists(doctype, document.name):
			frappe.has_permission(doctype, "read", doc=document.name, throw=True)
		else:
			frappe.has_permission(doctype, "read", throw=True)
	else:
		document = frappe.get_doc(doctype, name)
		document.check_permission("read")

	return build_flowchart(document)


def get_default_lag_mins() -> float:
	gap = get_mins_between_operations()
	return gap.days * 1440 + gap.hours * 60 + gap.minutes


def build_flowchart(document) -> dict:
	rows = sorted(document.get("operations") or [], key=lambda row: row.idx or 0)
	raw_sequence_ids = [row.get("sequence_id") or None for row in rows]
	normalized = normalize_sequence_ids(raw_sequence_ids)
	ordered = sorted(zip(rows, normalized, raw_sequence_ids), key=lambda item: (item[1], item[0].idx))

	nodes = [
		OperationNode(
			key=row.name,
			idx=row.idx,
			sequence_id=sequence_id,
			operation=row.operation,
			workstation=row.get("workstation"),
			time_in_mins=flt(row.get("time_in_mins")),
			predecessor_relation=row.get("predecessor_relation") or None,
			lag_mins=flt(row.get("lag_mins")),
			bom=row.get("bom"),
		)
		for row, sequence_id, raw_sequence_id in ordered
	]
	default_lag_mins = get_default_lag_mins()
	graph = build_operation_graph(
		nodes,
		[raw_sequence_id for row, sequence_id, raw_sequence_id in ordered],
		default_lag_mins,
		check_sequence=document.doctype in ("BOM", "Routing"),
	)

	release = None
	deadline_mins = None
	if document.doctype == "Work Order":
		release = (
			get_datetime(document.planned_start_date) if document.get("planned_start_date") else None
		)
		if release and document.get("expected_delivery_date"):
			deadline = get_datetime(document.expected_delivery_date)
			deadline_mins = time_diff_in_seconds(deadline, release) / 60

	windows, makespan = compute_time_windows(graph.nodes, graph.edges, deadline_mins)
	binding = binding_edges(graph.edges, windows, graph.nodes)
	critical = {key for key, window in windows.items() if window.slack <= TOLERANCE}

	if deadline_mins is not None and makespan > deadline_mins + TOLERANCE:
		graph.issues.append(
			Issue(
				"warning",
				_(
					"The operations need {0} min but only {1} min are available before the expected delivery date."
				).format(round(makespan), round(deadline_mins)),
			)
		)

	def absolute(offset_mins):
		if release is None:
			return None
		return str(add_to_date(release, minutes=offset_mins))

	return {
		"doctype": document.doctype,
		"release": str(release) if release else None,
		"makespan_mins": makespan,
		"default_lag_mins": default_lag_mins,
		"nodes": [
			{
				"key": node.key,
				"idx": node.idx,
				"sequence_id": node.sequence_id,
				"operation": node.operation,
				"workstation": node.workstation,
				"bom": node.bom,
				"time_in_mins": node.time_in_mins,
				"earliest_start_mins": windows[node.key].earliest_start,
				"latest_start_mins": windows[node.key].latest_start,
				"slack_mins": windows[node.key].slack,
				"earliest_start": absolute(windows[node.key].earliest_start),
				"critical": node.key in critical,
			}
			for node in graph.nodes
		],
		"edges": [
			{
				"predecessor": edge.predecessor,
				"successor": edge.successor,
				"relation": edge.relation,
				"abbreviation": RELATION_ABBREVIATIONS[edge.relation],
				"lag_mins": edge.lag_mins,
				"source": edge.source,
				"binding": (edge.predecessor, edge.successor) in binding,
				"critical": (edge.predecessor, edge.successor) in binding
				and edge.predecessor in critical
				and edge.successor in critical,
			}
			for edge in graph.edges
		],
		"issues": [
			{"severity": issue.severity, "message": issue.message, "key": issue.key}
			for issue in graph.issues
		],
	}
