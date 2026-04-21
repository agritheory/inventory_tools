# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import safe_json_loads
import networkx as nx
import numpy as np

GRAPH_CACHE_KEY = "warehouse_plan:graph:{}"


class WarehousePlan(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link | None
		floor_plan: DF.AttachImage | None
		group_warehouse: DF.Link | None
		horizontal: DF.Float
		matrix: DF.LongText | None
		offset: DF.Data | None
		pickup_point_x: DF.Int
		pickup_point_y: DF.Int
		uom: DF.Link | None
		vertical: DF.Float
	# end: auto-generated types

	@property
	def graph(self) -> "Grid_TSP | None":
		g = frappe.cache.get_value(GRAPH_CACHE_KEY.format(self.name))
		if g is None and self.matrix:
			g = self._build_graph()
			frappe.cache.set_value(GRAPH_CACHE_KEY.format(self.name), g)
		return g

	def _build_graph(self) -> "Grid_TSP":
		grid = np.array(safe_json_loads(self.matrix))
		return Grid_TSP(grid, scale=self.horizontal / grid.shape[1])

	def on_load(self):
		if self.matrix and not frappe.cache.get_value(GRAPH_CACHE_KEY.format(self.name)):
			frappe.cache.set_value(GRAPH_CACHE_KEY.format(self.name), self._build_graph())

	def on_save(self):
		if self.matrix:
			frappe.cache.set_value(GRAPH_CACHE_KEY.format(self.name), self._build_graph())
		else:
			frappe.cache.delete_value(GRAPH_CACHE_KEY.format(self.name))

	@frappe.whitelist()
	def get_plan_warehouses(self):
		return frappe.get_all(
			"Warehouse",
			filters={"warehouse_plan": self.name, "warehouse_plan_coordinates": ["is", "set"]},
			fields=["name", "warehouse_plan_coordinates", "rotation", "accessible_path"],
		)

	@frappe.whitelist()
	def set_warehouse_plan_details(self, warehouses: list):
		Wh = frappe.qb.DocType("Warehouse")
		existing_warehouses = (
			frappe.qb.from_(Wh).select(Wh.name).where(Wh.warehouse_plan == self.name).run(pluck=True)
		)

		for warehouse in warehouses:
			wh_name = warehouse.get("warehouse_name")
			(
				frappe.qb.update(Wh)
				.set(Wh.warehouse_plan, self.name)
				.set(Wh.warehouse_plan_coordinates, warehouse.get("coordinates"))
				.set(Wh.rotation, warehouse.get("rotation"))
				.set(Wh.accessible_path, warehouse.get("accessible_path"))
				.where(Wh.name == wh_name)
				.run()
			)
			if wh_name in existing_warehouses:
				existing_warehouses.remove(wh_name)

		if existing_warehouses:
			(
				frappe.qb.update(Wh)
				.set(Wh.warehouse_plan, None)
				.set(Wh.warehouse_plan_coordinates, None)
				.set(Wh.rotation, 0)
				.set(Wh.accessible_path, None)
				.where(Wh.name.isin(existing_warehouses))
				.run()
			)

	@frappe.whitelist()
	def get_warehouse_dimensions(self, warehouse: str):
		warehouse_doc = frappe.get_doc("Warehouse", warehouse)
		dimensions = frappe.get_all(
			"Physical Dimension",
			filters={"reference_doctype": "Warehouse", "reference_document": warehouse_doc.name},
			fields=["item_length", "item_width", "uom"],
		)

		if not dimensions:
			return {}

		dimension = dimensions[0]

		# convert warehouse dimension UOM using UOM Conversion records
		if dimension.uom != self.uom:
			uom_conversion = frappe.get_all(
				"UOM Conversion Factor",
				filters={"category": "Length", "from_uom": dimension.uom, "to_uom": self.uom},
				pluck="value",
				limit=1,
			)

			if uom_conversion:
				dimension.item_length *= uom_conversion[0]
				dimension.item_width *= uom_conversion[0]

		return dimension


class Grid_TSP:
	"""Constructs a graph from a 2D grid and solves path and TSP problems using NetworkX.

	Navigable nodes are grid cells with value 1. Nodes connect to their west and north neighbors,
	with edge weights scaled by the provided factor. The class offers methods to validate graph
	connectivity, convert between grid positions and node indices, compute shortest paths, approximate
	a TSP route for given nodes, and visualize the grid and routes for debugging.

	Attributes:
	        grid (np.ndarray): 2D array representing the grid (1 indicates a pathway).
	        scale (int or float): Factor to scale edge weights.
	        G (nx.Graph): Graph built from the grid.
	"""

	def __init__(self, grid, scale=1):
		self.grid = grid
		self.scale = scale
		self.G = nx.Graph()
		self.make_graph()

	def make_graph(self):
		x_shape = self.grid.shape[1]
		for n, pos in enumerate(np.ndindex(self.grid.shape)):
			x = pos[1]
			y = pos[0]
			if self.grid[pos] == 1:
				self.G.add_node(n, pos=(x, -y))
				# Add edged to north and west neighbors if pathway
				if x > 0 and self.grid[y, x - 1] == 1:
					self.G.add_edge(n, n - 1, weight=self.scale)
				if y > 0 and self.grid[y - 1, x] == 1:
					north_neighbor = n - x_shape
					self.G.add_edge(n, north_neighbor, weight=self.scale)

	def validate(self) -> bool:
		if nx.is_connected(self.G):
			return True
		else:
			return False

	def pos2node(self, pos: tuple) -> int:
		return pos[1] * self.grid.shape[1] + pos[0]

	def node2pos(self, node: int) -> tuple:
		return (node // self.grid.shape[1], node % self.grid.shape[1])

	def find_path(self, start: int, end: int):
		try:
			path = nx.shortest_path(self.G, start, end)
		except nx.NetworkXNoPath:
			print("No path found between the given nodes.")
			path = []
		except nx.NodeNotFound as e:
			print(f"Error: {e}")
			path = []
		except Exception as e:
			print(f"Unexpected error: {e}")
			path = []

		distance = sum(self.G[u][v]["weight"] for u, v in zip(path, path[1:]))
		return path, distance

	def tsp(self, pickup_node: list, nodes: list, debug: bool = False):
		tsp = nx.approximation.traveling_salesman_problem
		pickup_list = pickup_node + nodes
		try:
			tsp_route = tsp(self.G, nodes=pickup_list)
		except KeyError as e:
			frappe.throw(
				"Route optimization failed: One or more pickup locations are not found in the current grid overlay. <br>"
				+ "This may be due to a mismatch between the pickup list and the warehouse layout. Missing node: {str(e)}",
				frappe.ValidationError,
			)
		pickup_order = list(dict.fromkeys(node for node in tsp_route if node in pickup_list))[1:]
		if debug:
			tsp_distance = sum(self.G[u][v]["weight"] for u, v in zip(tsp_route, tsp_route[1:]))
			return pickup_order, tsp_route, tsp_distance
		else:
			return (pickup_order, None, None)

	def _plot(self, tsp_route: list[int] | None = None) -> None:
		"""Debug plot of the grid and (optional) TSP route."""
		import matplotlib.pyplot as plt

		plt.imshow(self.grid, cmap="gray")
		plt.grid(True)

		if tsp_route:
			# node2pos(wp) returns a (row:int, col:int) tuple
			coords: list[tuple[int, int]] = [self.node2pos(wp) for wp in tsp_route]
			rows, cols = zip(*coords)  # unzip into two sequences of ints
			plt.plot(cols, rows, "r-")  # x = cols, y = rows

		plt.show()
