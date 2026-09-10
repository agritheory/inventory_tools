# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

from frappe import _


def get_data(data):
	data.fieldname = data.get("fieldname") or "reference_document"
	data.setdefault("dynamic_links", {})
	data["dynamic_links"]["reference_document"] = ["Shipment Parcel Template", "reference_doctype"]

	has_physical_dimension = any(
		"Physical Dimension" in (group.get("items") or []) for group in data.get("transactions") or []
	)
	if not has_physical_dimension:
		data.setdefault("transactions", []).append(
			{"label": _("Physical Dimensions"), "items": ["Physical Dimension"]},
		)

	return data
