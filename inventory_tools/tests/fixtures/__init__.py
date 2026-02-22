# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import json
from pathlib import Path

# Get the directory where this file is located
_fixtures_dir = Path(__file__).parent


def _load_json(filename: str):
	"""Load a JSON fixture file."""
	filepath = _fixtures_dir / f"{filename}.json"
	with open(filepath) as f:
		return json.load(f)


# Load all fixtures
attributes = _load_json("attributes")
boms = _load_json("boms")
customers = _load_json("customers")
item_dimensions = _load_json("item_dimensions")
items = _load_json("items")
items_stockentry = _load_json("items_stockentry")
operations = _load_json("operations")
sales_orders = _load_json("sales_orders")
specifications = _load_json("specifications")
suppliers = _load_json("suppliers")
warehouse_dimensions = _load_json("warehouse_dimensions")
warehouse_locations = _load_json("warehouse_locations")
warehouse_plan_matrix = _load_json("warehouse_plan_matrix")
workstations = _load_json("workstations")

__all__ = [
	"attributes",
	"boms",
	"customers",
	"item_dimensions",
	"items",
	"items_stockentry",
	"operations",
	"sales_orders",
	"specifications",
	"suppliers",
	"warehouse_dimensions",
	"warehouse_locations",
	"warehouse_plan_matrix",
	"workstations",
]
