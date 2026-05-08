# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def physical_dimension_item_uom_query(doctype, txt, searchfield, start, page_len, filters):
	args = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	item_code = args.get("item_code")
	if not item_code:
		return []

	allowed = sorted(allowed_item_uoms(item_code))
	t = (txt or "").strip().lower()

	matched = [u for u in allowed if not t or t in u.lower()]

	page = matched[start : start + page_len]
	return [[u, u] for u in page]


class PhysicalDimension(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		dimension_type: DF.Literal["Exterior", "Interior"]
		item_height: DF.Float
		item_length: DF.Float
		item_uom: DF.Link | None
		item_volume: DF.Float
		item_weight: DF.Float
		item_width: DF.Float
		orientation: DF.Check
		reference_doctype: DF.Link
		reference_document: DF.DynamicLink
		uom: DF.Link
		visualization: DF.AttachImage | None

	# end: auto-generated types

	def autoname(self):
		if self.reference_doctype == "Item" and self.item_uom:
			self.name = f"{self.reference_document}-{self.dimension_type}-{self.uom}-{self.item_uom}"
		else:
			self.name = f"{self.reference_document}-{self.dimension_type}-{self.uom}"

	def validate(self):
		if self.reference_doctype != "Item":
			self.item_uom = None

		if self.reference_doctype == "Item" and self.reference_document:
			if not self.item_uom:
				frappe.throw(
					_("Item UOM is required when Reference Doctype is Item."), title=_("Missing Item UOM")
				)

			valid = allowed_item_uoms(self.reference_document)
			if self.item_uom not in valid:
				frappe.throw(
					_('Item UOM "{0}" is not valid for Item {1}. Allowed: {2}').format(
						frappe.bold(self.item_uom),
						frappe.bold(self.reference_document),
						", ".join(sorted(valid)) or _("(none defined)"),
					),
					title=_("Invalid Item UOM"),
				)

			dup = frappe.db.exists(
				"Physical Dimension",
				{
					"reference_doctype": "Item",
					"reference_document": self.reference_document,
					"dimension_type": self.dimension_type,
					"uom": self.uom,
					"item_uom": self.item_uom,
				},
			)

			if dup and (self.is_new() or dup != self.name):
				frappe.throw(
					_(
						"A Physical Dimension already exists with the same Reference, Dimension Type, UOM and Item UOM ({0})."
					).format(
						frappe.bold(dup),
					),
					title=_("Duplicate Physical Dimension"),
				)

		elif self.reference_doctype and self.reference_doctype != "Item" and self.reference_document:
			dup = frappe.db.exists(
				"Physical Dimension",
				{
					"reference_doctype": self.reference_doctype,
					"reference_document": self.reference_document,
					"dimension_type": self.dimension_type,
					"uom": self.uom,
				},
			)
			if dup and (self.is_new() or dup != self.name):
				frappe.throw(
					_("A Physical Dimension already exists for this reference ({0}).").format(frappe.bold(dup)),
					title=_("Duplicate Physical Dimension"),
				)

		self.calculate_item_volume()

	def calculate_item_volume(self):
		self.item_volume = flt(self.item_height) * flt(self.item_length) * flt(self.item_width)


def allowed_item_uoms(item_code):
	"""Stock UOM plus every alternate UOM on the Item."""
	stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
	if not stock_uom:
		return set()
	alts = frappe.get_all(
		"UOM Conversion Detail",
		filters={"parenttype": "Item", "parent": item_code},
		pluck="uom",
	)
	return {stock_uom} | {u for u in alts if u}
