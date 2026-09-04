# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Date
from frappe.utils import flt, getdate

LINE_SOURCES = [
	{
		"parent_doctype": "Quotation",
		"child_doctype": "Quotation Item",
		"date_field": "transaction_date",
		"qty_field": "qty",
		"stock_qty_field": "stock_qty",
		"uom_field": "uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "Sales Order",
		"child_doctype": "Sales Order Item",
		"date_field": "transaction_date",
		"qty_field": "qty",
		"stock_qty_field": "stock_qty",
		"uom_field": "uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "Delivery Note",
		"child_doctype": "Delivery Note Item",
		"date_field": "posting_date",
		"qty_field": "qty",
		"stock_qty_field": "stock_qty",
		"uom_field": "uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "Sales Invoice",
		"child_doctype": "Sales Invoice Item",
		"date_field": "posting_date",
		"qty_field": "qty",
		"stock_qty_field": "stock_qty",
		"uom_field": "uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "POS Invoice",
		"child_doctype": "POS Invoice Item",
		"date_field": "posting_date",
		"qty_field": "qty",
		"stock_qty_field": "stock_qty",
		"uom_field": "uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "Request for Quotation",
		"child_doctype": "Request for Quotation Item",
		"date_field": "transaction_date",
		"qty_field": "qty",
		"stock_qty_field": "stock_qty",
		"uom_field": "uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "Supplier Quotation",
		"child_doctype": "Supplier Quotation Item",
		"date_field": "transaction_date",
		"qty_field": "qty",
		"stock_qty_field": "stock_qty",
		"uom_field": "uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "Purchase Order",
		"child_doctype": "Purchase Order Item",
		"date_field": "transaction_date",
		"qty_field": "qty",
		"stock_qty_field": "stock_qty",
		"uom_field": "uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "Purchase Receipt",
		"child_doctype": "Purchase Receipt Item",
		"date_field": "posting_date",
		"qty_field": "qty",
		"stock_qty_field": "stock_qty",
		"uom_field": "uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "Purchase Invoice",
		"child_doctype": "Purchase Invoice Item",
		"date_field": "posting_date",
		"qty_field": "qty",
		"stock_qty_field": "stock_qty",
		"uom_field": "uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "Material Request",
		"child_doctype": "Material Request Item",
		"date_field": "transaction_date",
		"qty_field": "qty",
		"stock_qty_field": "stock_qty",
		"uom_field": "uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "Stock Entry",
		"child_doctype": "Stock Entry Detail",
		"date_field": "posting_date",
		"qty_field": "qty",
		"stock_qty_field": "transfer_qty",
		"uom_field": "uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "Pick List",
		"child_doctype": "Pick List Item",
		"date_field": "creation",
		"qty_field": "qty",
		"stock_qty_field": "stock_qty",
		"uom_field": "uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "Subcontracting Order",
		"child_doctype": "Subcontracting Order Item",
		"date_field": "transaction_date",
		"qty_field": "qty",
		"stock_qty_field": "qty",
		"uom_field": "stock_uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "Subcontracting Receipt",
		"child_doctype": "Subcontracting Receipt Item",
		"date_field": "posting_date",
		"qty_field": "qty",
		"stock_qty_field": "qty",
		"uom_field": "stock_uom",
		"stock_uom_field": "stock_uom",
	},
	{
		"parent_doctype": "Quotation",
		"child_doctype": "Packed Item",
		"date_field": "transaction_date",
		"qty_field": "qty",
		"stock_uom_from_item": True,
		"uom_field": "uom",
	},
	{
		"parent_doctype": "Sales Order",
		"child_doctype": "Packed Item",
		"date_field": "transaction_date",
		"qty_field": "qty",
		"stock_uom_from_item": True,
		"uom_field": "uom",
	},
	{
		"parent_doctype": "Delivery Note",
		"child_doctype": "Packed Item",
		"date_field": "posting_date",
		"qty_field": "qty",
		"stock_uom_from_item": True,
		"uom_field": "uom",
	},
	{
		"parent_doctype": "Sales Invoice",
		"child_doctype": "Packed Item",
		"date_field": "posting_date",
		"qty_field": "qty",
		"stock_uom_from_item": True,
		"uom_field": "uom",
	},
	{
		"parent_doctype": "POS Invoice",
		"child_doctype": "Packed Item",
		"date_field": "posting_date",
		"qty_field": "qty",
		"stock_uom_from_item": True,
		"uom_field": "uom",
	},
]

STATUS_TO_DOCSTATUS = {
	"Draft": 0,
	"Submitted": 1,
	"Cancelled": 2,
}


@frappe.whitelist()
def get_document_type_options(txt=""):
	parent_doctypes = sorted({source["parent_doctype"] for source in LINE_SOURCES})
	if txt:
		parent_doctypes = [name for name in parent_doctypes if txt.lower() in name.lower()]
	return [{"value": name, "description": ""} for name in parent_doctypes]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	columns = get_columns(filters)
	lines = find_undeclared_uom_lines(filters)
	data = group_rows(lines, filters.get("group_by") or "UOM Pair")
	return columns, data


def validate_filters(filters):
	if not filters.get("company"):
		frappe.throw(_("Company is required"))
	if not filters.get("from_date"):
		frappe.throw(_("From Date is required"))
	if not filters.get("to_date"):
		frappe.throw(_("To Date is required"))
	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date"))


def get_columns(filters):
	group_by = filters.get("group_by") or "UOM Pair"
	group_label = _("UOM Pair") if group_by == "UOM Pair" else _("Document")

	return [
		{"label": group_label, "fieldname": "group_label", "fieldtype": "Data", "width": 260},
		{
			"label": _("Transaction Type"),
			"fieldname": "transaction_type",
			"fieldtype": "Link",
			"options": "DocType",
			"width": 140,
		},
		{
			"label": _("Transaction"),
			"fieldname": "transaction",
			"fieldtype": "Dynamic Link",
			"options": "transaction_type",
			"width": 160,
		},
		{"label": _("Row"), "fieldname": "row", "fieldtype": "Int", "width": 60},
		{
			"label": _("Item"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{
			"label": _("Undeclared UOM"),
			"fieldname": "undeclared_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 120,
		},
		{
			"label": _("Stock UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
		},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 90},
		{"label": _("Stock Qty"), "fieldname": "stock_qty", "fieldtype": "Float", "width": 90},
		{
			"label": _("Conversion Factor"),
			"fieldname": "conversion_factor",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("Identity Conversion"),
			"fieldname": "identity_conversion",
			"fieldtype": "Check",
			"width": 130,
		},
		{
			"label": _("Declared UOMs"),
			"fieldname": "declared_uoms",
			"fieldtype": "Data",
			"width": 220,
		},
		{"label": _("Line Count"), "fieldname": "line_count", "fieldtype": "Int", "width": 90},
		{
			"label": _("Identity Count"),
			"fieldname": "identity_count",
			"fieldtype": "Int",
			"width": 110,
		},
	]


def find_undeclared_uom_lines(filters):
	docstatus_values = get_docstatus_values(filters)
	selected_sources = get_selected_sources(filters)
	lines = []

	for source in selected_sources:
		lines.extend(query_source(source, filters, docstatus_values))

	if not lines:
		return []

	declared_uoms = get_declared_uoms_by_item({line["item_code"] for line in lines})
	for line in lines:
		line["declared_uoms"] = declared_uoms.get(line["item_code"], "")
		line["identity_conversion"] = is_identity_conversion(line)

	return lines


def get_docstatus_values(filters):
	statuses = filters.get("status")
	if not statuses:
		return [STATUS_TO_DOCSTATUS["Submitted"]]
	if isinstance(statuses, str):
		statuses = [status.strip() for status in statuses.split(",") if status.strip()]
	elif not isinstance(statuses, (list, tuple)):
		statuses = [statuses]
	return [STATUS_TO_DOCSTATUS[status] for status in statuses if status in STATUS_TO_DOCSTATUS]


def get_selected_sources(filters):
	document_types = filters.get("document_type")
	if not document_types:
		return LINE_SOURCES
	if isinstance(document_types, str):
		document_types = [value.strip() for value in document_types.split(",") if value.strip()]
	elif not isinstance(document_types, (list, tuple)):
		document_types = [document_types]
	return [source for source in LINE_SOURCES if source["parent_doctype"] in document_types]


def query_source(source, filters, docstatus_values):
	parent = DocType(source["parent_doctype"])
	child = DocType(source["child_doctype"])
	ucd = DocType("UOM Conversion Detail")
	uom_column = getattr(child, source["uom_field"])
	stock_uom_column = getattr(child, source.get("stock_uom_field") or source["uom_field"])
	qty_column = getattr(child, source["qty_field"])

	ucd_join = (ucd.parent == child.item_code) & (ucd.parenttype == "Item") & (ucd.uom == uom_column)

	if source.get("stock_uom_from_item"):
		item = DocType("Item")
		query = (
			frappe.qb.from_(child)
			.inner_join(parent)
			.on(child.parent == parent.name)
			.left_join(item)
			.on(child.item_code == item.name)
			.left_join(ucd)
			.on(ucd_join)
			.select(
				parent.name.as_("transaction"),
				child.idx.as_("row"),
				child.item_code,
				uom_column.as_("undeclared_uom"),
				child.conversion_factor,
				qty_column.as_("qty"),
				item.stock_uom.as_("stock_uom"),
				(child.qty * child.conversion_factor).as_("stock_qty"),
			)
		)
	else:
		stock_qty_column = getattr(child, source["stock_qty_field"])
		query = (
			frappe.qb.from_(child)
			.inner_join(parent)
			.on(child.parent == parent.name)
			.left_join(ucd)
			.on(ucd_join)
			.select(
				parent.name.as_("transaction"),
				child.idx.as_("row"),
				child.item_code,
				uom_column.as_("undeclared_uom"),
				child.conversion_factor,
				qty_column.as_("qty"),
				stock_uom_column.as_("stock_uom"),
				stock_qty_column.as_("stock_qty"),
			)
		)

	query = (
		query.where(ucd.name.isnull())
		.where(child.parenttype == source["parent_doctype"])
		.where(child.item_code.isnotnull())
		.where(child.item_code != "")
		.where(uom_column.isnotnull())
		.where(uom_column != "")
		.where(parent.company == filters.company)
		.where(parent.docstatus.isin(docstatus_values))
	)

	date_field = source["date_field"]
	if date_field == "creation":
		query = query.where(Date(parent.creation)[filters.from_date : filters.to_date])
	else:
		query = query.where(getattr(parent, date_field)[filters.from_date : filters.to_date])

	if filters.get("item_code"):
		query = query.where(child.item_code == filters.item_code)
	if filters.get("undeclared_uom"):
		query = query.where(uom_column == filters.undeclared_uom)

	rows = query.run(as_dict=True)
	for row in rows:
		row["transaction_type"] = source["parent_doctype"]
	return rows


def get_declared_uoms_by_item(item_codes):
	rows = frappe.get_all(
		"UOM Conversion Detail",
		filters={"parent": ["in", list(item_codes)], "parenttype": "Item"},
		fields=["parent", "uom"],
		order_by="parent asc, idx asc",
	)
	declared = {}
	for row in rows:
		declared.setdefault(row.parent, []).append(row.uom)
	return {item_code: ", ".join(uoms) for item_code, uoms in declared.items()}


def is_identity_conversion(line):
	return flt(line.get("conversion_factor")) == 1 and line.get("undeclared_uom") != line.get(
		"stock_uom"
	)


def group_rows(lines, group_by):
	if not lines:
		return []

	output = []
	if group_by == "Document":
		lines.sort(key=lambda row: (row["transaction_type"], row["transaction"], row["row"]))
		current_key = None
		group_lines = []

		for line in lines:
			key = (line["transaction_type"], line["transaction"])
			if key != current_key:
				if group_lines:
					output.extend(build_document_group(current_key, group_lines))
				current_key = key
				group_lines = [line]
			else:
				group_lines.append(line)

		if group_lines:
			output.extend(build_document_group(current_key, group_lines))
		return output

	lines.sort(
		key=lambda row: (
			row["undeclared_uom"],
			row["stock_uom"],
			row["transaction_type"],
			row["transaction"],
			row["row"],
		)
	)
	current_key = None
	group_lines = []

	for line in lines:
		key = (line["undeclared_uom"], line["stock_uom"])
		if key != current_key:
			if group_lines:
				output.extend(build_uom_pair_group(current_key, group_lines))
			current_key = key
			group_lines = [line]
		else:
			group_lines.append(line)

	if group_lines:
		output.extend(build_uom_pair_group(current_key, group_lines))
	return output


def build_uom_pair_group(key, group_lines):
	undeclared_uom, stock_uom = key
	identity_count = sum(1 for line in group_lines if line.get("identity_conversion"))
	header = frappe._dict(
		{
			"group_label": f"{undeclared_uom} → {stock_uom}",
			"line_count": len(group_lines),
			"identity_count": identity_count,
			"indent": 0,
		}
	)
	children = [frappe._dict({**line, "indent": 1}) for line in group_lines]
	return [header, *children]


def build_document_group(key, group_lines):
	transaction_type, transaction = key
	identity_count = sum(1 for line in group_lines if line.get("identity_conversion"))
	header = frappe._dict(
		{
			"group_label": f"{transaction_type} {transaction}",
			"line_count": len(group_lines),
			"identity_count": identity_count,
			"indent": 0,
		}
	)
	children = [frappe._dict({**line, "indent": 1}) for line in group_lines]
	return [header, *children]
