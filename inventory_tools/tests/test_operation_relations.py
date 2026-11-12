# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest

from inventory_tools.inventory_tools.scheduling.flowchart import get_operation_flowchart
from inventory_tools.inventory_tools.scheduling.precedence import (
	FINISH_TO_FINISH,
	FINISH_TO_START,
	START_TO_FINISH,
	START_TO_START,
	OperationNode,
	binding_edges,
	build_operation_graph,
	compute_time_windows,
	normalize_sequence_ids,
	sequence_issues,
)


def make_nodes(rows):
	"""rows: (sequence_id, time_in_mins, relation, lag_mins)"""
	sequence_ids = normalize_sequence_ids([row[0] for row in rows])
	return [
		OperationNode(
			key=str(idx),
			idx=idx,
			sequence_id=sequence_id,
			operation=f"Op {idx}",
			workstation=None,
			time_in_mins=time_in_mins,
			predecessor_relation=relation,
			lag_mins=lag_mins,
		)
		for idx, ((raw, time_in_mins, relation, lag_mins), sequence_id) in enumerate(
			zip(rows, sequence_ids), start=1
		)
	]


def solve(rows, default_lag_mins=10, deadline_mins=None):
	nodes = make_nodes(rows)
	graph = build_operation_graph(nodes, [row[0] for row in rows], default_lag_mins, True)
	windows, makespan = compute_time_windows(graph.nodes, graph.edges, deadline_mins)
	return graph, windows, makespan


def test_normalize_sequence_ids():
	assert normalize_sequence_ids([None, None, None]) == [1, 2, 3]
	assert normalize_sequence_ids([1, 1, None, 3]) == [1, 1, 2, 3]


def test_sequence_issues_match_work_order_validation():
	assert sequence_issues([None, None], [1, 2]) == []
	assert sequence_issues([1, 1, 2], [1, 2, 3]) == []
	messages = [issue.message for issue in sequence_issues([2, 4, 3, None], [1, 2, 3, 4])]
	assert any("first Sequence ID must be 1" in message for message in messages)
	assert any("jumps from 2 to 4" in message for message in messages)
	assert any("lower than the row before" in message for message in messages)
	assert any("all or none" in message for message in messages)


def test_blank_relations_reproduce_erpnext_planning():
	"""Blank relations: Finish to Start plus the default gap between groups, and
	rows sharing a Sequence ID start together."""
	graph, windows, makespan = solve(
		[(1, 5, None, 0), (2, 30, None, 0), (2, 5, None, 0), (3, 10, None, 0)]
	)
	assert [windows[key].earliest_start for key in "1234"] == [0, 15, 15, 55]
	assert makespan == 65
	assert windows["3"].slack == 25
	assert {edge.source for edge in graph.edges} == {"default", "sequence_group"}


def test_lag_is_ignored_without_relation():
	graph, windows, makespan = solve([(None, 5, None, 0), (None, 5, None, 99)])
	assert windows["2"].earliest_start == 15


@pytest.mark.parametrize(
	"relation, lag, expected_start",
	[
		(FINISH_TO_START, 0, 20),
		(FINISH_TO_START, 5, 25),
		(START_TO_START, 2, 2),
		(FINISH_TO_FINISH, 5, 15),
		(START_TO_FINISH, 30, 20),
	],
)
def test_relation_bounds(relation, lag, expected_start):
	"""Predecessor runs 20 min, successor 10 min."""
	graph, windows, makespan = solve([(None, 20, None, 0), (None, 10, relation, lag)])
	assert windows["2"].earliest_start == expected_start


def test_negative_lag_warns():
	graph, windows, makespan = solve([(None, 20, None, 0), (None, 10, START_TO_FINISH, -5)])
	assert [issue.message for issue in graph.issues] == [
		"Negative lag (-5 min) lets this operation lead its predecessor."
	]


def test_unknown_relation_is_an_error_and_falls_back_to_default():
	graph, windows, makespan = solve([(None, 20, None, 0), (None, 10, "Whenever", 0)])
	assert any(issue.severity == "error" for issue in graph.issues)
	assert windows["2"].earliest_start == 30


def test_relation_on_first_row_is_ignored_with_warning():
	graph, windows, makespan = solve([(None, 20, START_TO_START, 5), (None, 10, None, 0)])
	assert windows["1"].earliest_start == 0
	assert any("first operation" in issue.message for issue in graph.issues)


def test_explicit_relation_inside_first_group_uses_group_leader():
	graph, windows, makespan = solve([(1, 20, None, 0), (1, 10, FINISH_TO_START, 0)])
	assert windows["2"].earliest_start == 20


def test_deadline_sets_latest_starts():
	graph, windows, makespan = solve([(None, 20, None, 0), (None, 10, None, 0)], deadline_mins=100)
	assert makespan == 40
	assert windows["2"].latest_start == 90
	assert windows["1"].latest_start == 60


def test_binding_edges_follow_the_longest_predecessor():
	graph, windows, makespan = solve(
		[(1, 5, None, 0), (2, 30, None, 0), (2, 5, None, 0), (3, 10, None, 0)]
	)
	binding = binding_edges(graph.edges, windows, graph.nodes)
	assert ("2", "4") in binding
	assert ("3", "4") not in binding


@pytest.mark.order(140)
def test_pie_crust_bom_flowchart():
	"""The in-house Pie Crust fixture chills the crust while the tins are prepped."""
	bom = frappe.db.get_value(
		"BOM", {"item": "Pie Crust", "is_subcontracted": 0, "docstatus": 1}, "name"
	)
	assert bom, "In-house Pie Crust BOM missing in test data"
	data = get_operation_flowchart("BOM", bom)
	nodes = {node["operation"]: node for node in data["nodes"]}
	assert nodes["Chill Pie Crust Op"]["sequence_id"] == nodes["Prep Pie Tins Op"]["sequence_id"]
	assert nodes["Chill Pie Crust Op"]["critical"]
	assert not nodes["Prep Pie Tins Op"]["critical"]
	assert nodes["Prep Pie Tins Op"]["slack_mins"] == 25
	divide = next(
		edge for edge in data["edges"] if edge["successor"] == nodes["Divide Dough Op"]["key"]
	)
	assert divide["relation"] == FINISH_TO_FINISH
	assert divide["source"] == "explicit"
	assert not [issue for issue in data["issues"] if issue["severity"] == "error"]


@pytest.mark.order(140)
def test_bom_copies_relations_from_routing():
	bom = frappe.get_doc(
		"BOM",
		frappe.db.get_value(
			"BOM", {"item": "Bayberry Pie Filling", "is_default": 1, "docstatus": 1}, "name"
		),
	)
	assert bom.routing == "Pie Filling"
	cook = next(row for row in bom.operations if row.operation == "Cook Pie Filling Operation")
	assert cook.predecessor_relation == START_TO_START
	assert cook.lag_mins == 2


@pytest.mark.order(141)
def test_work_order_operations_copy_relations_from_bom():
	bom = frappe.db.get_value(
		"BOM", {"item": "Gooseberry Pie", "is_default": 1, "docstatus": 1}, "name"
	)
	assert bom, "Gooseberry Pie BOM missing in test data"
	from erpnext.manufacturing.doctype.work_order.work_order import make_work_order

	wo = make_work_order(bom, "Gooseberry Pie", qty=5, company="Ambrosia Pie Company")
	box = next(row for row in wo.operations if row.operation == "Box Pie Op")
	assert box.predecessor_relation == FINISH_TO_FINISH
	assert box.lag_mins == 5
	preheat = next(row for row in wo.operations if row.operation == "Preheat Oven Op")
	assemble = next(row for row in wo.operations if row.operation == "Assemble Pie Op")
	assert preheat.sequence_id == assemble.sequence_id == 1
