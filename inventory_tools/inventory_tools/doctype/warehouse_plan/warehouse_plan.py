# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class WarehousePlan(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link | None
		floor_plan: DF.AttachImage | None
		group_warehouse: DF.Link | None
		matrix: DF.LongText | None
	# end: auto-generated types
