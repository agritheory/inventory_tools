# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns(filters)
	data = []

	cycle = filters.get("cycle")
	if cycle == "Purchasing Cycle":
		data = get_purchasing_cycle_data(filters)
	elif cycle == "Sales Cycle":
		data = get_sales_cycle_data(filters)
	elif cycle == "Quotation Cycle":
		data = get_quotation_cycle_data(filters)

	return columns, data


def get_columns(filters):
	"""Define columns based on cycle and aggregation level"""
	cycle = filters.get("cycle")

	base_columns = [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
	]

	if cycle == "Purchasing Cycle":
		cycle_columns = [
			{
				"label": _("Purchase Order"),
				"fieldname": "purchase_order",
				"fieldtype": "Link",
				"options": "Purchase Order",
				"width": 150,
			},
			{"label": _("PO Qty"), "fieldname": "po_qty", "fieldtype": "Float", "width": 100},
			{"label": _("PO Rate"), "fieldname": "po_rate", "fieldtype": "Currency", "width": 120},
			{
				"label": _("Purchase Receipt"),
				"fieldname": "purchase_receipt",
				"fieldtype": "Link",
				"options": "Purchase Receipt",
				"width": 150,
			},
			{"label": _("PR Qty"), "fieldname": "pr_qty", "fieldtype": "Float", "width": 100},
			{"label": _("PR Qty Var"), "fieldname": "pr_qty_variance", "fieldtype": "Float", "width": 100},
			{"label": _("PR Rate"), "fieldname": "pr_rate", "fieldtype": "Currency", "width": 120},
			{
				"label": _("PR Total Qty Var"),
				"fieldname": "pr_total_qty_variance",
				"fieldtype": "Data",
				"width": 120,
			},
			{
				"label": _("PR Rate Var"),
				"fieldname": "pr_rate_variance",
				"fieldtype": "Currency",
				"width": 120,
			},
			{
				"label": _("Purchase Invoice"),
				"fieldname": "purchase_invoice",
				"fieldtype": "Link",
				"options": "Purchase Invoice",
				"width": 150,
			},
			{"label": _("PI Qty"), "fieldname": "pi_qty", "fieldtype": "Float", "width": 100},
			{"label": _("PI Qty Var"), "fieldname": "pi_qty_variance", "fieldtype": "Float", "width": 100},
			{
				"label": _("PI Total Qty Var"),
				"fieldname": "pi_total_qty_variance",
				"fieldtype": "Data",
				"width": 120,
			},
			{"label": _("PI Rate"), "fieldname": "pi_rate", "fieldtype": "Currency", "width": 120},
			{
				"label": _("PI Rate Var"),
				"fieldname": "pi_rate_variance",
				"fieldtype": "Currency",
				"width": 120,
			},
		]
	elif cycle == "Sales Cycle":
		cycle_columns = [
			{
				"label": _("Sales Order"),
				"fieldname": "sales_order",
				"fieldtype": "Link",
				"options": "Sales Order",
				"width": 150,
			},
			{"label": _("SO Qty"), "fieldname": "so_qty", "fieldtype": "Float", "width": 100},
			{"label": _("SO Rate"), "fieldname": "so_rate", "fieldtype": "Currency", "width": 120},
			{
				"label": _("Delivery Note"),
				"fieldname": "delivery_note",
				"fieldtype": "Link",
				"options": "Delivery Note",
				"width": 150,
			},
			{"label": _("DN Qty"), "fieldname": "dn_qty", "fieldtype": "Float", "width": 100},
			{"label": _("DN Qty Var"), "fieldname": "dn_qty_variance", "fieldtype": "Float", "width": 100},
			{
				"label": _("DN Total Qty Var"),
				"fieldname": "dn_total_qty_variance",
				"fieldtype": "Data",
				"width": 120,
			},
			{"label": _("DN Rate"), "fieldname": "dn_rate", "fieldtype": "Currency", "width": 120},
			{
				"label": _("DN Rate Var"),
				"fieldname": "dn_rate_variance",
				"fieldtype": "Currency",
				"width": 120,
			},
			{
				"label": _("Sales Invoice"),
				"fieldname": "sales_invoice",
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"width": 150,
			},
			{"label": _("SI Qty"), "fieldname": "si_qty", "fieldtype": "Float", "width": 100},
			{"label": _("SI Qty Var"), "fieldname": "si_qty_variance", "fieldtype": "Float", "width": 100},
			{
				"label": _("SI Total Qty Var"),
				"fieldname": "si_total_qty_variance",
				"fieldtype": "Data",
				"width": 120,
			},
			{"label": _("SI Rate"), "fieldname": "si_rate", "fieldtype": "Currency", "width": 120},
			{
				"label": _("SI Rate Var"),
				"fieldname": "si_rate_variance",
				"fieldtype": "Currency",
				"width": 120,
			},
		]
	else:  # Quotation Cycle
		cycle_columns = [
			{
				"label": _("Request for Quotation"),
				"fieldname": "request_for_quotation",
				"fieldtype": "Link",
				"options": "Request for Quotation",
				"width": 150,
			},
			{"label": _("RFQ Qty"), "fieldname": "rfq_qty", "fieldtype": "Float", "width": 100},
			{
				"label": _("Supplier Quotation"),
				"fieldname": "supplier_quotation",
				"fieldtype": "Link",
				"options": "Supplier Quotation",
				"width": 150,
			},
			{"label": _("SQ Qty"), "fieldname": "sq_qty", "fieldtype": "Float", "width": 100},
			{"label": _("SQ Qty Var"), "fieldname": "sq_qty_variance", "fieldtype": "Float", "width": 100},
			{
				"label": _("SQ Total Qty Var"),
				"fieldname": "sq_total_qty_variance",
				"fieldtype": "Data",
				"width": 120,
			},
			{"label": _("SQ Rate"), "fieldname": "sq_rate", "fieldtype": "Currency", "width": 120},
			{
				"label": _("Purchase Order"),
				"fieldname": "purchase_order",
				"fieldtype": "Link",
				"options": "Purchase Order",
				"width": 150,
			},
			{"label": _("PO Qty"), "fieldname": "po_qty", "fieldtype": "Float", "width": 100},
			{"label": _("PO Qty Var"), "fieldname": "po_qty_variance", "fieldtype": "Float", "width": 100},
			{
				"label": _("PO Total Qty Var"),
				"fieldname": "po_total_qty_variance",
				"fieldtype": "Data",
				"width": 120,
			},
			{"label": _("PO Rate"), "fieldname": "po_rate", "fieldtype": "Currency", "width": 120},
			{
				"label": _("PO Rate Var"),
				"fieldname": "po_rate_variance",
				"fieldtype": "Currency",
				"width": 120,
			},
		]

	return base_columns + cycle_columns


def get_field_precision(doctype, fieldname):
	"""Get precision for a field from DocType definition"""
	try:
		df = frappe.get_meta(doctype).get_field(fieldname)
		if df:
			return df.precision or 6
	except Exception:
		pass
	return 6


def compare_values(val1, val2, precision):
	"""Compare two values with precision tolerance"""
	if val1 is None or val2 is None:
		return val1 == val2
	return round(val1, precision) == round(val2, precision)


def calculate_total_variances(
	data, demand_doc_field, demand_qty_field, receipt_qty_field, invoice_qty_field=None
):
	"""
	Calculate total quantity variances by grouping on demand document + item.
	Adds total_variance fields to each row showing the aggregate variance for that group.

	Args:
	        data: List of row dictionaries
	        demand_doc_field: Field name for demand document (e.g., 'purchase_order')
	        demand_qty_field: Field name for demand quantity (e.g., 'po_qty')
	        receipt_qty_field: Field name for receipt quantity (e.g., 'pr_qty')
	        invoice_qty_field: Optional field name for invoice quantity
	"""
	from collections import defaultdict

	# Group by demand document + item
	groups = defaultdict(lambda: {"demand_qty": None, "receipt_qtys": [], "invoice_qtys": []})

	for row in data:
		key = (row.get(demand_doc_field), row.get("item_code"))

		if groups[key]["demand_qty"] is None:
			groups[key]["demand_qty"] = row.get(demand_qty_field)

		if row.get(receipt_qty_field) is not None:
			groups[key]["receipt_qtys"].append(row.get(receipt_qty_field))

		if invoice_qty_field and row.get(invoice_qty_field) is not None:
			groups[key]["invoice_qtys"].append(row.get(invoice_qty_field))

	# Calculate total variances for each group
	total_variances = {}
	for key, group in groups.items():
		demand_qty = group["demand_qty"]

		if demand_qty is not None:
			# Receipt total variance
			if group["receipt_qtys"]:
				total_receipt_qty = sum(group["receipt_qtys"])
				receipt_variance = total_receipt_qty - demand_qty
			else:
				receipt_variance = None

			# Invoice total variance
			if invoice_qty_field and group["invoice_qtys"]:
				total_invoice_qty = sum(group["invoice_qtys"])
				invoice_variance = total_invoice_qty - demand_qty
			else:
				invoice_variance = None

			total_variances[key] = {"receipt": receipt_variance, "invoice": invoice_variance}

	# Add total variances to each row
	# Build field names by replacing '_qty' with '_total_qty_variance'
	receipt_variance_base = receipt_qty_field.replace("_qty", "")  # e.g., 'pr_qty' -> 'pr'
	receipt_total_field = (
		f"{receipt_variance_base}_total_qty_variance"  # e.g., 'pr_total_qty_variance'
	)

	invoice_total_field = None
	if invoice_qty_field:
		invoice_variance_base = invoice_qty_field.replace("_qty", "")  # e.g., 'pi_qty' -> 'pi'
		invoice_total_field = (
			f"{invoice_variance_base}_total_qty_variance"  # e.g., 'pi_total_qty_variance'
		)

	for row in data:
		key = (row.get(demand_doc_field), row.get("item_code"))
		if key in total_variances:
			row[receipt_total_field] = total_variances[key]["receipt"]
			if invoice_total_field:
				row[invoice_total_field] = total_variances[key]["invoice"]

	return data


def get_purchasing_cycle_data(filters):
	"""
	Compare Purchase Order, Purchase Receipt, and Purchase Invoice
	Using Purchase Order Item as the anchor/demand signal
	"""

	PurchaseReceipt = DocType("Purchase Receipt")
	PurchaseReceiptItem = DocType("Purchase Receipt Item")
	PurchaseOrder = DocType("Purchase Order")
	PurchaseOrderItem = DocType("Purchase Order Item")
	PurchaseInvoice = DocType("Purchase Invoice")
	PurchaseInvoiceItem = DocType("Purchase Invoice Item")

	query = (
		frappe.qb.from_(PurchaseOrderItem)
		.inner_join(PurchaseOrder)
		.on(PurchaseOrder.name == PurchaseOrderItem.parent)
		.left_join(PurchaseReceiptItem)
		.on(PurchaseReceiptItem.purchase_order_item == PurchaseOrderItem.name)
		.left_join(PurchaseReceipt)
		.on(PurchaseReceipt.name == PurchaseReceiptItem.parent)
		.left_join(PurchaseInvoiceItem)
		.on(
			(
				(PurchaseInvoiceItem.purchase_receipt == PurchaseReceiptItem.parent)
				& (PurchaseInvoiceItem.pr_detail == PurchaseReceiptItem.name)
			)
			| (
				(PurchaseInvoiceItem.purchase_order == PurchaseOrderItem.parent)
				& (PurchaseInvoiceItem.po_detail == PurchaseOrderItem.name)
			)
		)
		.left_join(PurchaseInvoice)
		.on(PurchaseInvoice.name == PurchaseInvoiceItem.parent)
		.select(
			PurchaseOrderItem.item_code,
			PurchaseOrderItem.item_name,
			PurchaseOrderItem.parent.as_("purchase_order"),
			PurchaseOrderItem.qty.as_("po_qty"),
			PurchaseOrderItem.rate.as_("po_rate"),
			PurchaseOrder.status.as_("po_status"),
			PurchaseReceiptItem.parent.as_("purchase_receipt"),
			PurchaseReceiptItem.qty.as_("pr_qty"),
			PurchaseReceiptItem.rate.as_("pr_rate"),
			PurchaseReceipt.status.as_("pr_status"),
			PurchaseInvoiceItem.parent.as_("purchase_invoice"),
			PurchaseInvoiceItem.qty.as_("pi_qty"),
			PurchaseInvoiceItem.rate.as_("pi_rate"),
			PurchaseInvoice.status.as_("pi_status"),
			PurchaseOrder.transaction_date.as_("po_date"),
		)
		.where(PurchaseOrder.docstatus == 1)
	)

	# Apply filters
	if filters.get("company"):
		query = query.where(PurchaseOrder.company == filters.get("company"))

	if filters.get("start_date"):
		query = query.where(PurchaseOrder.transaction_date >= filters.get("start_date"))

	if filters.get("end_date"):
		query = query.where(PurchaseOrder.transaction_date <= filters.get("end_date"))

	# Add per-doctype filtering if provided
	if filters.get("purchase_order"):
		query = query.where(PurchaseOrder.name == filters.get("purchase_order"))
	if filters.get("purchase_receipt"):
		query = query.where(PurchaseReceipt.name == filters.get("purchase_receipt"))
	if filters.get("purchase_invoice"):
		query = query.where(PurchaseInvoice.name == filters.get("purchase_invoice"))

	query = query.orderby(PurchaseOrder.transaction_date, order=frappe.qb.desc)
	query = query.orderby(PurchaseOrderItem.item_code)

	data = query.run(as_dict=True)

	# Get field precisions
	qty_precision = get_field_precision("Purchase Order Item", "qty")
	rate_precision = get_field_precision("Purchase Order Item", "rate")

	# Calculate variances and filter for discrepancies
	result = []
	per_doctype_mode = bool(
		filters.get("purchase_order")
		or filters.get("purchase_receipt")
		or filters.get("purchase_invoice")
	)

	for row in data:
		has_discrepancy = False

		# Determine if we should ignore small discrepancies based on closed status
		ignore_discrepancy = not per_doctype_mode and (row.get("po_status") == "Closed")

		# Calculate quantity variances
		if row.pr_qty is not None and row.po_qty is not None:
			row["pr_qty_variance"] = row.pr_qty - row.po_qty
			if not ignore_discrepancy and not compare_values(row.pr_qty, row.po_qty, qty_precision):
				has_discrepancy = True

		if row.pi_qty is not None and row.po_qty is not None:
			row["pi_qty_variance"] = row.pi_qty - row.po_qty
			if not ignore_discrepancy and not compare_values(row.pi_qty, row.po_qty, qty_precision):
				has_discrepancy = True

		# Calculate rate variances
		if row.pr_rate is not None and row.po_rate is not None:
			row["pr_rate_variance"] = row.pr_rate - row.po_rate
			if not ignore_discrepancy and not compare_values(row.pr_rate, row.po_rate, rate_precision):
				has_discrepancy = True

		if row.pi_rate is not None and row.po_rate is not None:
			row["pi_rate_variance"] = row.pi_rate - row.po_rate
			if not ignore_discrepancy and not compare_values(row.pi_rate, row.po_rate, rate_precision):
				has_discrepancy = True

		# Check for missing documents
		if not row.purchase_receipt:
			has_discrepancy = True
		if not row.purchase_invoice:
			has_discrepancy = True

		# Only include rows with discrepancies
		if has_discrepancy:
			# Clean up status fields before returning
			row.pop("po_status", None)
			row.pop("pr_status", None)
			row.pop("pi_status", None)
			result.append(row)

	# Calculate total variances across all PRs/PIs for each PO+Item
	result = calculate_total_variances(
		result,
		demand_doc_field="purchase_order",
		demand_qty_field="po_qty",
		receipt_qty_field="pr_qty",
		invoice_qty_field="pi_qty",
	)

	return result


def get_sales_cycle_data(filters):
	"""
	Compare Sales Order, Delivery Note, and Sales Invoice
	Using Sales Order Item as the anchor/demand signal
	"""

	DeliveryNote = DocType("Delivery Note")
	DeliveryNoteItem = DocType("Delivery Note Item")
	SalesOrder = DocType("Sales Order")
	SalesOrderItem = DocType("Sales Order Item")
	SalesInvoice = DocType("Sales Invoice")
	SalesInvoiceItem = DocType("Sales Invoice Item")

	query = (
		frappe.qb.from_(SalesOrderItem)
		.inner_join(SalesOrder)
		.on(SalesOrder.name == SalesOrderItem.parent)
		.left_join(DeliveryNoteItem)
		.on(DeliveryNoteItem.so_detail == SalesOrderItem.name)
		.left_join(DeliveryNote)
		.on(DeliveryNote.name == DeliveryNoteItem.parent)
		.left_join(SalesInvoiceItem)
		.on(
			(
				(SalesInvoiceItem.delivery_note == DeliveryNoteItem.parent)
				& (SalesInvoiceItem.dn_detail == DeliveryNoteItem.name)
			)
			| (
				(SalesInvoiceItem.sales_order == SalesOrderItem.parent)
				& (SalesInvoiceItem.so_detail == SalesOrderItem.name)
			)
		)
		.left_join(SalesInvoice)
		.on(SalesInvoice.name == SalesInvoiceItem.parent)
		.select(
			SalesOrderItem.item_code,
			SalesOrderItem.item_name,
			SalesOrderItem.parent.as_("sales_order"),
			SalesOrderItem.qty.as_("so_qty"),
			SalesOrderItem.rate.as_("so_rate"),
			SalesOrder.status.as_("so_status"),
			DeliveryNoteItem.parent.as_("delivery_note"),
			DeliveryNoteItem.qty.as_("dn_qty"),
			DeliveryNoteItem.rate.as_("dn_rate"),
			DeliveryNote.status.as_("dn_status"),
			SalesInvoiceItem.parent.as_("sales_invoice"),
			SalesInvoiceItem.qty.as_("si_qty"),
			SalesInvoiceItem.rate.as_("si_rate"),
			SalesInvoice.status.as_("si_status"),
			SalesOrder.transaction_date.as_("so_date"),
		)
		.where(SalesOrder.docstatus == 1)
	)

	# Apply filters
	if filters.get("company"):
		query = query.where(SalesOrder.company == filters.get("company"))

	if filters.get("start_date"):
		query = query.where(SalesOrder.transaction_date >= filters.get("start_date"))

	if filters.get("end_date"):
		query = query.where(SalesOrder.transaction_date <= filters.get("end_date"))

	# Add per-doctype filtering if provided
	if filters.get("sales_order"):
		query = query.where(SalesOrder.name == filters.get("sales_order"))
	if filters.get("delivery_note"):
		query = query.where(DeliveryNote.name == filters.get("delivery_note"))
	if filters.get("sales_invoice"):
		query = query.where(SalesInvoice.name == filters.get("sales_invoice"))

	query = query.orderby(SalesOrder.transaction_date, order=frappe.qb.desc)
	query = query.orderby(SalesOrderItem.item_code)

	data = query.run(as_dict=True)

	# Get field precisions
	qty_precision = get_field_precision("Sales Order Item", "qty")
	rate_precision = get_field_precision("Sales Order Item", "rate")

	# Calculate variances and filter for discrepancies
	result = []
	per_doctype_mode = bool(
		filters.get("sales_order") or filters.get("delivery_note") or filters.get("sales_invoice")
	)

	for row in data:
		has_discrepancy = False

		# Determine if we should ignore small discrepancies based on closed status
		ignore_discrepancy = not per_doctype_mode and (row.get("so_status") == "Closed")

		# Calculate quantity variances
		if row.dn_qty is not None and row.so_qty is not None:
			row["dn_qty_variance"] = row.dn_qty - row.so_qty
			if not ignore_discrepancy and not compare_values(row.dn_qty, row.so_qty, qty_precision):
				has_discrepancy = True

		if row.si_qty is not None and row.so_qty is not None:
			row["si_qty_variance"] = row.si_qty - row.so_qty
			if not ignore_discrepancy and not compare_values(row.si_qty, row.so_qty, qty_precision):
				has_discrepancy = True

		# Calculate rate variances
		if row.dn_rate is not None and row.so_rate is not None:
			row["dn_rate_variance"] = row.dn_rate - row.so_rate
			if not ignore_discrepancy and not compare_values(row.dn_rate, row.so_rate, rate_precision):
				has_discrepancy = True

		if row.si_rate is not None and row.so_rate is not None:
			row["si_rate_variance"] = row.si_rate - row.so_rate
			if not ignore_discrepancy and not compare_values(row.si_rate, row.so_rate, rate_precision):
				has_discrepancy = True

		# Check for missing documents
		if not row.delivery_note:
			has_discrepancy = True
		if not row.sales_invoice:
			has_discrepancy = True

		# Only include rows with discrepancies
		if has_discrepancy:
			# Clean up status fields before returning
			row.pop("so_status", None)
			row.pop("dn_status", None)
			row.pop("si_status", None)
			result.append(row)

	# Calculate total variances across all DNs/SIs for each SO+Item
	result = calculate_total_variances(
		result,
		demand_doc_field="sales_order",
		demand_qty_field="so_qty",
		receipt_qty_field="dn_qty",
		invoice_qty_field="si_qty",
	)

	return result


def get_quotation_cycle_data(filters):
	"""
	Compare Request for Quotation, Supplier Quotation, and Purchase Order
	Using Request for Quotation Item as the anchor/demand signal
	"""

	SupplierQuotation = DocType("Supplier Quotation")
	SupplierQuotationItem = DocType("Supplier Quotation Item")
	RequestForQuotation = DocType("Request for Quotation")
	RequestForQuotationItem = DocType("Request for Quotation Item")
	PurchaseOrder = DocType("Purchase Order")
	PurchaseOrderItem = DocType("Purchase Order Item")

	query = (
		frappe.qb.from_(RequestForQuotationItem)
		.inner_join(RequestForQuotation)
		.on(RequestForQuotation.name == RequestForQuotationItem.parent)
		.left_join(SupplierQuotationItem)
		.on(SupplierQuotationItem.request_for_quotation_item == RequestForQuotationItem.name)
		.left_join(SupplierQuotation)
		.on(SupplierQuotation.name == SupplierQuotationItem.parent)
		.left_join(PurchaseOrderItem)
		.on(
			(PurchaseOrderItem.supplier_quotation == SupplierQuotationItem.parent)
			& (PurchaseOrderItem.item_code == SupplierQuotationItem.item_code)
		)
		.left_join(PurchaseOrder)
		.on(PurchaseOrder.name == PurchaseOrderItem.parent)
		.select(
			RequestForQuotationItem.item_code,
			RequestForQuotationItem.item_name,
			RequestForQuotationItem.parent.as_("request_for_quotation"),
			RequestForQuotationItem.qty.as_("rfq_qty"),
			RequestForQuotation.status.as_("rfq_status"),
			SupplierQuotationItem.parent.as_("supplier_quotation"),
			SupplierQuotationItem.qty.as_("sq_qty"),
			SupplierQuotationItem.rate.as_("sq_rate"),
			SupplierQuotation.status.as_("sq_status"),
			PurchaseOrderItem.parent.as_("purchase_order"),
			PurchaseOrderItem.qty.as_("po_qty"),
			PurchaseOrderItem.rate.as_("po_rate"),
			PurchaseOrder.status.as_("po_status"),
			RequestForQuotation.transaction_date.as_("rfq_date"),
		)
		.where(RequestForQuotation.docstatus == 1)
	)

	# Apply filters
	if filters.get("company"):
		query = query.where(RequestForQuotation.company == filters.get("company"))

	if filters.get("start_date"):
		query = query.where(RequestForQuotation.transaction_date >= filters.get("start_date"))

	if filters.get("end_date"):
		query = query.where(RequestForQuotation.transaction_date <= filters.get("end_date"))

	# Add per-doctype filtering if provided
	if filters.get("request_for_quotation"):
		query = query.where(RequestForQuotation.name == filters.get("request_for_quotation"))
	if filters.get("supplier_quotation"):
		query = query.where(SupplierQuotation.name == filters.get("supplier_quotation"))
	if filters.get("purchase_order"):
		query = query.where(PurchaseOrder.name == filters.get("purchase_order"))

	query = query.orderby(RequestForQuotation.transaction_date, order=frappe.qb.desc)
	query = query.orderby(RequestForQuotationItem.item_code)

	data = query.run(as_dict=True)

	# Get field precisions
	qty_precision = get_field_precision("Request for Quotation Item", "qty")
	rate_precision = get_field_precision("Supplier Quotation Item", "rate")

	# Calculate variances and filter for discrepancies
	result = []
	per_doctype_mode = bool(
		filters.get("request_for_quotation")
		or filters.get("supplier_quotation")
		or filters.get("purchase_order")
	)

	for row in data:
		has_discrepancy = False

		# Determine if we should ignore small discrepancies based on closed status
		ignore_discrepancy = not per_doctype_mode and (
			row.get("rfq_status") == "Closed"
			or row.get("sq_status") == "Closed"
			or row.get("po_status") == "Closed"
		)

		# Calculate quantity variances (against RFQ as baseline)
		if row.sq_qty is not None and row.rfq_qty is not None:
			row["sq_qty_variance"] = row.sq_qty - row.rfq_qty
			if not ignore_discrepancy and not compare_values(row.sq_qty, row.rfq_qty, qty_precision):
				has_discrepancy = True

		if row.po_qty is not None and row.rfq_qty is not None:
			row["po_qty_variance"] = row.po_qty - row.rfq_qty
			if not ignore_discrepancy and not compare_values(row.po_qty, row.rfq_qty, qty_precision):
				has_discrepancy = True

		# Calculate rate variances (RFQ doesn't have rate, so compare PO to SQ)
		if row.po_rate is not None and row.sq_rate is not None:
			row["po_rate_variance"] = row.po_rate - row.sq_rate
			if not ignore_discrepancy and not compare_values(row.po_rate, row.sq_rate, rate_precision):
				has_discrepancy = True

		# Check for missing documents
		if not row.supplier_quotation:
			has_discrepancy = True
		if not row.purchase_order:
			has_discrepancy = True

		# Only include rows with discrepancies
		if has_discrepancy:
			# Clean up status fields before returning
			row.pop("rfq_status", None)
			row.pop("sq_status", None)
			row.pop("po_status", None)
			result.append(row)

	# Calculate total variances across all SQs/POs for each RFQ+Item
	result = calculate_total_variances(
		result,
		demand_doc_field="request_for_quotation",
		demand_qty_field="rfq_qty",
		receipt_qty_field="sq_qty",
		invoice_qty_field="po_qty",
	)

	return result
