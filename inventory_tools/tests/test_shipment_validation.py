import frappe
import pytest
from erpnext.stock.doctype.shipment.shipment import Shipment

from inventory_tools.inventory_tools.overrides.shipment import InventoryToolsShipment


def make_shipment(monkeypatch, rows, alternative=False):
	shipment = object.__new__(InventoryToolsShipment)
	shipment.shipment_delivery_note = [frappe._dict(idx=i, **row) for i, row in enumerate(rows, 1)]
	monkeypatch.setattr(
		InventoryToolsShipment,
		"uses_alternative_sales_workflow_without_delivery_note",
		lambda self: alternative,
	)
	return shipment


def test_sales_order_rows_skip_delivery_note_validation(monkeypatch):
	shipment = make_shipment(
		monkeypatch,
		[{"against_sales_order": "SO-1"}, {"so_detail": "SO-ITEM-2"}],
		alternative=True,
	)

	def unexpected_validation(self, row):
		pytest.fail("Sales Order-only rows must not be validated as Delivery Notes")

	monkeypatch.setattr(Shipment, "validate_delivery_note_row", unexpected_validation)
	shipment.validate_delivery_notes()


@pytest.mark.parametrize("alternative", [False, True])
def test_missing_delivery_note_requires_enabled_workflow_and_sales_order(monkeypatch, alternative):
	rows = [{}] if alternative else [{"against_sales_order": "SO-1"}]
	shipment = make_shipment(monkeypatch, rows, alternative)
	monkeypatch.setattr(frappe, "_", lambda message: message)

	def throw(message):
		raise frappe.ValidationError(message)

	monkeypatch.setattr(frappe, "throw", throw)
	with pytest.raises(frappe.ValidationError, match="Delivery Note is required"):
		shipment.validate_delivery_notes()


def test_item_rows_validate_each_delivery_note_and_preserve_amounts(monkeypatch):
	shipment = make_shipment(
		monkeypatch,
		[
			{"delivery_note": "DN-1", "dn_detail": "ITEM-1", "grand_total": 10},
			{"delivery_note": "DN-1", "dn_detail": "ITEM-2", "grand_total": 20},
			{"delivery_note": "DN-2", "grand_total": 0},
		],
	)
	validated = []

	def validate(self, row):
		validated.append(row.delivery_note)
		row.grand_total = 30

	monkeypatch.setattr(Shipment, "validate_delivery_note_row", validate)
	shipment.validate_delivery_notes()
	assert validated == ["DN-1", "DN-2"]
	assert [row.grand_total for row in shipment.shipment_delivery_note] == [10, 20, 30]


def test_linked_delivery_note_errors_propagate_in_alternative_workflow(monkeypatch):
	shipment = make_shipment(
		monkeypatch,
		[{"against_sales_order": "SO-1"}, {"delivery_note": "DN-1", "grand_total": 10}],
		alternative=True,
	)

	def validate(self, row):
		raise frappe.ValidationError("Delivery Note must be submitted")

	monkeypatch.setattr(Shipment, "validate_delivery_note_row", validate)
	with pytest.raises(frappe.ValidationError, match="must be submitted"):
		shipment.validate_delivery_notes()
