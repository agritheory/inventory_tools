# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""
Precedence between the operations of one Routing, BOM, or Work Order.

Blank relation fields reproduce ERPNext's own planning in
`WorkOrder.set_operation_start_end_time`: each sequence group starts after the
previous group finishes plus "Time Between Operations", and rows within a group
start together. An explicit `predecessor_relation` replaces that default for its
row, and its `lag_mins` is used as given (including 0).

This module does not import frappe so it can be tested without a site.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

FINISH_TO_START = "Finish to Start"
START_TO_START = "Start to Start"
FINISH_TO_FINISH = "Finish to Finish"
START_TO_FINISH = "Start to Finish"
RELATIONS = (FINISH_TO_START, START_TO_START, FINISH_TO_FINISH, START_TO_FINISH)
RELATION_ABBREVIATIONS = {
	FINISH_TO_START: "FS",
	START_TO_START: "SS",
	FINISH_TO_FINISH: "FF",
	START_TO_FINISH: "SF",
}

TOLERANCE = 1e-6


@dataclass(frozen=True)
class OperationNode:
	key: str
	idx: int
	sequence_id: int
	operation: str
	workstation: str | None
	time_in_mins: float
	predecessor_relation: str | None = None
	lag_mins: float = 0.0
	bom: str | None = None


@dataclass(frozen=True)
class PrecedenceEdge:
	predecessor: str
	successor: str
	relation: str
	lag_mins: float
	source: str  # "explicit", "default", "sequence_group"


@dataclass(frozen=True)
class TimeWindow:
	key: str
	earliest_start: float
	latest_start: float

	@property
	def slack(self) -> float:
		return self.latest_start - self.earliest_start


@dataclass
class Issue:
	severity: str  # "error" or "warning"
	message: str
	key: str | None = None


@dataclass
class OperationGraph:
	nodes: list[OperationNode]
	edges: list[PrecedenceEdge]
	issues: list[Issue] = field(default_factory=list)


def normalize_sequence_ids(raw_sequence_ids: Sequence[int | None]) -> list[int]:
	"""All blank means one row per group (ERPNext Work Order rule); otherwise a
	blank takes the previous value plus one (Routing rule)."""
	if not any(raw_sequence_ids):
		return list(range(1, len(raw_sequence_ids) + 1))
	normalized = []
	previous = 0
	for value in raw_sequence_ids:
		current = int(value) if value else previous + 1
		normalized.append(current)
		previous = current
	return normalized


def sequence_issues(raw_sequence_ids: Sequence[int | None], idxs: Sequence[int]) -> list[Issue]:
	"""Sequence IDs that ERPNext accepts on Routing or BOM but rejects on every
	Work Order made from them (`WorkOrder.validate_operations_sequence`)."""
	if not any(raw_sequence_ids):
		return []
	issues = []
	if not all(raw_sequence_ids):
		issues.append(
			Issue(
				"warning",
				"Some operations have a Sequence ID and some don't. Work Orders need all or none.",
			)
		)
	previous = None
	for value, idx in zip(raw_sequence_ids, idxs):
		if not value:
			continue
		value = int(value)
		if previous is None and value != 1:
			issues.append(Issue("warning", f"Row {idx}: the first Sequence ID must be 1 for Work Orders."))
		elif previous is not None and value < previous:
			issues.append(Issue("warning", f"Row {idx}: Sequence ID {value} is lower than the row before."))
		elif previous is not None and value > previous + 1:
			issues.append(
				Issue(
					"warning",
					f"Row {idx}: Sequence ID jumps from {previous} to {value}. Work Orders don't allow gaps.",
				)
			)
		previous = value
	return issues


def group_nodes(nodes: Sequence[OperationNode]) -> list[list[OperationNode]]:
	groups: list[list[OperationNode]] = []
	for node in nodes:
		if groups and groups[-1][0].sequence_id == node.sequence_id:
			groups[-1].append(node)
		else:
			groups.append([node])
	return groups


def build_precedence_edges(
	nodes: Sequence[OperationNode], default_lag_mins: float
) -> tuple[list[PrecedenceEdge], list[Issue]]:
	"""Nodes must already be in route order (sequence_id, then idx).

	- Every row in a group gets an edge from every row of the previous group:
	  its own relation and lag, or Finish to Start plus `default_lag_mins`.
	- A row other than the first in its group, with a blank relation, starts
	  with the group's first row (Start to Start, lag 0).
	- In the first group there is no previous group, so an explicit relation on
	  a row other than the first applies against the group's first row.
	"""
	edges: list[PrecedenceEdge] = []
	issues: list[Issue] = []
	groups = group_nodes(nodes)
	for group_index, group in enumerate(groups):
		first = group[0]
		previous_group = groups[group_index - 1] if group_index else []
		for position, node in enumerate(group):
			pred_rel = node.predecessor_relation
			explicit = bool(pred_rel)
			if explicit and pred_rel not in RELATIONS:
				issues.append(Issue("error", f"Unknown relation '{pred_rel}'.", node.key))
				explicit = False
			if explicit and pred_rel is not None:
				relation = pred_rel
				lag = float(node.lag_mins or 0)
			else:
				relation = FINISH_TO_START
				lag = float(default_lag_mins)
			for predecessor in previous_group:
				edges.append(
					PrecedenceEdge(
						predecessor.key, node.key, relation, lag, "explicit" if explicit else "default"
					)
				)
			if position == 0:
				if explicit and not previous_group:
					issues.append(
						Issue(
							"warning", "The first operation has no predecessor; its relation is ignored.", node.key
						)
					)
				continue
			if not explicit:
				edges.append(PrecedenceEdge(first.key, node.key, START_TO_START, 0.0, "sequence_group"))
			elif not previous_group:
				edges.append(PrecedenceEdge(first.key, node.key, relation, lag, "explicit"))
	issues.extend(relation_issues(nodes))
	return edges, issues


def relation_issues(nodes: Iterable[OperationNode]) -> list[Issue]:
	issues = []
	for node in nodes:
		if not node.predecessor_relation:
			continue
		if (node.lag_mins or 0) < 0:
			issues.append(
				Issue(
					"warning",
					f"Negative lag ({node.lag_mins:g} min) lets this operation lead its predecessor.",
					node.key,
				)
			)
	return issues


def edge_bound(
	edge: PrecedenceEdge, starts: dict[str, float], durations: dict[str, float]
) -> float:
	"""Lower bound on the successor's start implied by one edge."""
	start = starts[edge.predecessor]
	predecessor_duration = durations[edge.predecessor]
	successor_duration = durations[edge.successor]
	if edge.relation == FINISH_TO_START:
		return start + predecessor_duration + edge.lag_mins
	if edge.relation == START_TO_START:
		return start + edge.lag_mins
	if edge.relation == FINISH_TO_FINISH:
		return start + predecessor_duration + edge.lag_mins - successor_duration
	return start + edge.lag_mins - successor_duration


def latest_start_bound(
	edge: PrecedenceEdge, latest_starts: dict[str, float], durations: dict[str, float]
) -> float:
	"""Upper bound on the predecessor's start implied by one edge."""
	latest = latest_starts[edge.successor]
	predecessor_duration = durations[edge.predecessor]
	successor_duration = durations[edge.successor]
	if edge.relation == FINISH_TO_START:
		return latest - predecessor_duration - edge.lag_mins
	if edge.relation == START_TO_START:
		return latest - edge.lag_mins
	if edge.relation == FINISH_TO_FINISH:
		return latest + successor_duration - predecessor_duration - edge.lag_mins
	return latest + successor_duration - edge.lag_mins


def compute_time_windows(
	nodes: Sequence[OperationNode],
	edges: Sequence[PrecedenceEdge],
	deadline_mins: float | None = None,
) -> tuple[dict[str, TimeWindow], float]:
	"""Critical-path windows in minutes from the release (time 0), ignoring
	machine capacity. Nodes must be in route order, which is a topological order
	for edges from `build_precedence_edges`.

	Without a deadline, the latest finish is the earliest possible finish of the
	whole route, so slack is measured against the critical path.

	Returns the windows and the earliest possible finish of the route.
	"""
	durations = {node.key: float(node.time_in_mins or 0) for node in nodes}
	incoming: dict[str, list[PrecedenceEdge]] = {node.key: [] for node in nodes}
	outgoing: dict[str, list[PrecedenceEdge]] = {node.key: [] for node in nodes}
	for edge in edges:
		incoming[edge.successor].append(edge)
		outgoing[edge.predecessor].append(edge)

	earliest: dict[str, float] = {}
	for node in nodes:
		bounds = [edge_bound(edge, earliest, durations) for edge in incoming[node.key]]
		earliest[node.key] = max([0.0, *bounds])

	makespan = max((earliest[key] + durations[key] for key in earliest), default=0.0)
	end = makespan if deadline_mins is None else deadline_mins

	latest: dict[str, float] = {}
	for node in reversed(nodes):
		bounds = [latest_start_bound(edge, latest, durations) for edge in outgoing[node.key]]
		latest[node.key] = min([end - durations[node.key], *bounds])

	windows = {node.key: TimeWindow(node.key, earliest[node.key], latest[node.key]) for node in nodes}
	return windows, makespan


def binding_edges(
	edges: Sequence[PrecedenceEdge], windows: dict[str, TimeWindow], nodes: Sequence[OperationNode]
) -> set[tuple[str, str]]:
	"""Edges whose bound sets the successor's earliest start."""
	durations = {node.key: float(node.time_in_mins or 0) for node in nodes}
	starts = {key: window.earliest_start for key, window in windows.items()}
	return {
		(edge.predecessor, edge.successor)
		for edge in edges
		if abs(edge_bound(edge, starts, durations) - starts[edge.successor]) <= TOLERANCE
	}


def build_operation_graph(
	nodes: Sequence[OperationNode],
	raw_sequence_ids: Sequence[int | None],
	default_lag_mins: float,
	check_sequence: bool,
) -> OperationGraph:
	edges, issues = build_precedence_edges(nodes, default_lag_mins)
	if check_sequence:
		issues = sequence_issues(raw_sequence_ids, [node.idx for node in nodes]) + issues
	return OperationGraph(list(nodes), edges, issues)
