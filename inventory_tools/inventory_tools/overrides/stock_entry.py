# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import FinishedGoodError, StockEntry
from frappe import _
from frappe.utils import flt, cint

from inventory_tools.inventory_tools.overrides.inspection import (
	get_inspection_required,
	validate_inspection_with_company_scope,
)
from inventory_tools.inventory_tools.overrides.work_order import get_allowance_percentage
from inventory_tools.inventory_tools.doctype.workstation_operating_cost.workstation_operating_cost import (
	get_operating_costs_by_operation,
)


class InventoryToolsStockEntry(StockEntry):
	def check_if_operations_completed(self):
		"""
		HASH: 4dd9f0b25545a034ae3cc2012dc5a1049449c5b7
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/stock/doctype/stock_entry/stock_entry.py
		METHOD: check_if_operations_completed

		Original code checks that the stock entry amount plus what's already produced in the WO
		is not larger than any operation's completed quantity (plus the overallowance amount).
		Since customized code rewires so stock entries happen via a Job Card, the function now
		checks that the stock entry amount plus what's already been produced in the WO is not
		greater than the amount to be manufactured plus the overallowance amount.
		"""

		prod_order = frappe.get_doc("Work Order", self.work_order)
		allowance_percentage = get_allowance_percentage(self.company, self.bom_no)

		jc_qty = flt(
			self.fg_completed_qty
		)  # quantity manufactured and being entered in stock entry for this JC
		already_produced = flt(prod_order.produced_qty)  # quantity already manufactured for WO
		total_completed_qty = jc_qty + already_produced

		wo_to_man_qty = flt(prod_order.qty)
		allowed_qty = wo_to_man_qty * (
			1 + allowance_percentage / 100
		)  # amount to be manufactured on the WO including the overallowance amount

		if total_completed_qty > allowed_qty:
			work_order_link = frappe.utils.get_link_to_form("Work Order", self.work_order)
			frappe.throw(
				_(
					"Quantity manufactured in this Job Card of {0} plus quantity already produced for Work Order {1} of {2} is greater than the Work Order's quantity to manufacture of {3} plus the overproduction allowance of {4}%"
				).format(
					self.fg_completed_qty,
					work_order_link,
					already_produced,
					wo_to_man_qty,
					allowance_percentage,
				)
			)

	def validate_finished_goods(self):
		"""
		HASH: 4dd9f0b25545a034ae3cc2012dc5a1049449c5b7
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/stock/doctype/stock_entry/stock_entry.py
		METHOD: validate_finished_goods

		1. Check if FG exists (mfg, repack)
		2. Check if Multiple FG Items are present (mfg)
		3. Check FG Item and Qty against WO if present (mfg)
		"""

		production_item, wo_qty, finished_items = None, 0, []

		wo_details = frappe.db.get_value("Work Order", self.work_order, ["production_item", "qty"])
		if wo_details:
			production_item, wo_qty = wo_details

		for d in self.get("items"):
			if d.is_finished_item:
				if not self.work_order:
					# Independent MFG Entry/ Repack Entry, no WO to match against
					finished_items.append(d.item_code)
					continue

				if d.item_code != production_item:
					frappe.throw(
						_("Finished Item {0} does not match with Work Order {1}").format(
							d.item_code, self.work_order
						)
					)
				elif flt(d.qty) > flt(self.fg_completed_qty):
					frappe.throw(
						_("Quantity in row {0} ({1}) must be same as manufactured quantity {2}").format(
							d.idx, d.qty, self.fg_completed_qty
						)
					)

				finished_items.append(d.item_code)

		if not finished_items:
			frappe.throw(
				msg=_("There must be at least 1 Finished Good in this Stock Entry").format(self.name),
				title=_("Missing Finished Good"),
				exc=FinishedGoodError,
			)

		if self.purpose == "Manufacture":
			if len(set(finished_items)) > 1:
				frappe.throw(
					msg=_("Multiple items cannot be marked as finished item"),
					title=_("Note"),
					exc=FinishedGoodError,
				)

			allowance_percentage = get_allowance_percentage(self.company, self.bom_no)
			allowed_qty = wo_qty + ((allowance_percentage / 100) * wo_qty)

			# No work order could mean independent Manufacture entry, if so skip validation
			if self.work_order and self.fg_completed_qty > allowed_qty:
				frappe.throw(
					_("For quantity {0} should not be greater than work order quantity {1}").format(
						flt(self.fg_completed_qty), wo_qty
					)
				)

	def get_pending_raw_materials(self, backflush_based_on=None):
		"""
		HASH: 4dd9f0b25545a034ae3cc2012dc5a1049449c5b7
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/stock/doctype/stock_entry/stock_entry.py
		METHOD: get_pending_raw_materials

		issue (item quantity) that is pending to issue or desire to transfer,
		whichever is less
		"""

		item_dict = self.get_pro_order_required_items(backflush_based_on)

		max_qty = flt(self.pro_doc.qty)

		allow_overproduction = False
		overproduction_percentage = get_allowance_percentage(self.company, self.bom_no)

		to_transfer_qty = flt(self.pro_doc.material_transferred_for_manufacturing) + flt(
			self.fg_completed_qty
		)
		transfer_limit_qty = max_qty + ((max_qty * overproduction_percentage) / 100)

		if transfer_limit_qty >= to_transfer_qty:
			allow_overproduction = True

		for item, item_details in item_dict.items():
			pending_to_issue = flt(item_details.required_qty) - flt(item_details.transferred_qty)
			desire_to_transfer = flt(self.fg_completed_qty) * flt(item_details.required_qty) / max_qty

			if (
				desire_to_transfer <= pending_to_issue
				or (desire_to_transfer > 0 and backflush_based_on == "Material Transferred for Manufacture")
				or allow_overproduction
			):
				# "No need for transfer but qty still pending to transfer" case can occur
				# when transferring multiple RM in different Stock Entries
				item_dict[item]["qty"] = desire_to_transfer if (desire_to_transfer > 0) else pending_to_issue
			elif pending_to_issue > 0:
				item_dict[item]["qty"] = pending_to_issue
			else:
				item_dict[item]["qty"] = 0

		# delete items with 0 qty
		list_of_items = list(item_dict.keys())
		for item in list_of_items:
			if not item_dict[item]["qty"]:
				del item_dict[item]

		# show some message
		if not len(item_dict):
			frappe.msgprint(_("""All items have already been transferred for this Work Order."""))

		return item_dict

	@frappe.whitelist()
	def get_items(self):
		"""
		HASH: a5ed3a59450aae98bf3d9a59a8c7a8eddbb58f6b
		REPO: https://github.com/frappe/erpnext/
		PATH: erpnext/stock/doctype/stock_entry/stock_entry.py
		METHOD: get_items
		"""

		super().get_items()
		if self.work_order and self.purpose == "Manufacture":
			work_order = frappe.get_doc("Work Order", self.work_order)
			self.calculate_additional_costs(work_order)

	@frappe.whitelist()
	def calculate_additional_costs(stock_entry=None, work_order=None):
		from erpnext.manufacturing.doctype.bom.bom import add_non_stock_items_cost

		# Add non stock items cost in the additional cost
		stock_entry.additional_costs = []
		company_account = frappe.db.get_value(
			"Company",
			work_order.company,
			["expenses_included_in_valuation", "default_operating_cost_account"],
			as_dict=1,
		)

		expense_account = (
			company_account.default_operating_cost_account or company_account.expenses_included_in_valuation
		)
		add_non_stock_items_cost(stock_entry, work_order, expense_account)
		add_operations_cost(stock_entry, work_order, expense_account)

	def validate_qi_presence(self, row):
		settings = frappe.get_doc("Inventory Tools Settings", self.company)

		if settings.enable_quarantine_workflow:
			return

		super().validate_qi_presence(row)

	def validate_qi_submission(self, row):
		settings = frappe.get_doc("Inventory Tools Settings", self.company)

		if settings.enable_quarantine_workflow:
			return

		super().validate_qi_submission(row)

	def validate_inspection(self):
		validate_inspection_with_company_scope(self)


def add_operations_cost(stock_entry, work_order=None, expense_account=None):
	operating_costs = get_operating_costs_by_operation(
		work_order, stock_entry.bom_no, posting_date=stock_entry.posting_date
	)

	if operating_costs:
		for cost in operating_costs:
			stock_entry.append(
				"additional_costs",
				{
					"expense_account": cost.get("account"),
					"description": cost.get("description"),
					"amount": flt(cost.get("cost_per_unit")) * flt(stock_entry.fg_completed_qty),
				},
			)

	if work_order and work_order.additional_operating_cost and work_order.qty:
		additional_operating_cost_per_unit = flt(work_order.additional_operating_cost) / flt(
			work_order.qty
		)

		if additional_operating_cost_per_unit:
			stock_entry.append(
				"additional_costs",
				{
					"expense_account": expense_account,
					"description": "Additional Operating Cost",
					"amount": additional_operating_cost_per_unit * flt(stock_entry.fg_completed_qty),
				},
			)

	def get_max_operation_quantity():
		from frappe.query_builder.functions import Sum

		table = frappe.qb.DocType("Job Card")
		query = (
			frappe.qb.from_(table)
			.select(Sum(table.total_completed_qty).as_("qty"))
			.where(
				(table.docstatus == 1)
				& (table.work_order == work_order.name)
				& (table.is_corrective_job_card == 0)
			)
			.groupby(table.operation)
		)
		return min([d.qty for d in query.run(as_dict=True)], default=0)

	def get_utilised_corrective_cost():
		from frappe.query_builder.functions import Sum

		table = frappe.qb.DocType("Stock Entry")
		subquery = (
			frappe.qb.from_(table)
			.select(table.name)
			.where(
				(table.docstatus == 1)
				& (table.work_order == work_order.name)
				& (table.purpose == "Manufacture")
			)
		)
		table = frappe.qb.DocType("Landed Cost Taxes and Charges")
		query = (
			frappe.qb.from_(table)
			.select(Sum(table.amount).as_("amount"))
			.where(table.parent.isin(subquery) & (table.has_corrective_cost == 1))
		)
		return query.run(as_dict=True)[0].amount or 0

	if (
		work_order
		and work_order.corrective_operation_cost
		and cint(
			frappe.db.get_single_value(
				"Manufacturing Settings", "add_corrective_operation_cost_in_finished_good_valuation"
			)
		)
	):
		max_qty = get_max_operation_quantity() - work_order.produced_qty
		remaining_corrective_cost = work_order.corrective_operation_cost - get_utilised_corrective_cost()
		stock_entry.append(
			"additional_costs",
			{
				"expense_account": expense_account,
				"description": "Corrective Operation Cost",
				"has_corrective_cost": 1,
				"amount": remaining_corrective_cost / max_qty * flt(stock_entry.fg_completed_qty),
			},
		)


@frappe.whitelist()
@frappe.read_only()
def get_production_item_if_work_orders_for_required_item_exists(stock_entry_name: str) -> str:
	stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)

	if stock_entry.docstatus != 1 or stock_entry.stock_entry_type != "Manufacture":
		return ""

	production_item = frappe.get_value("Work Order", stock_entry.work_order, "production_item")
	WorkOrderItem = frappe.qb.DocType("Work Order Item")
	WorkOrder = frappe.qb.DocType("Work Order")
	work_orders = (
		frappe.qb.from_(WorkOrder)
		.join(WorkOrderItem)
		.on(WorkOrder.name == WorkOrderItem.parent)
		.select(WorkOrder.name, WorkOrder.status)
		.where(WorkOrderItem.item_code == production_item)
		.where(WorkOrder.status == "Not Started")
	).run()

	if len(work_orders):
		return production_item

	return ""


def get_quarantine_warehouses(company):
	"""Return all configured quarantine warehouses visible to a company."""
	settings = frappe.get_cached_doc("Inventory Tools Settings", company)
	warehouses = set()
	if settings.default_quarantine_warehouse:
		warehouses.add(settings.default_quarantine_warehouse)
	template_whs = frappe.get_all(
		"Quality Inspection Template",
		filters={"quarantine_warehouse": ["!=", ""]},
		pluck="quarantine_warehouse",
	)
	warehouses.update(w for w in template_whs if w)
	return warehouses


def validate_block_issue_from_quarantine(doc, method):
	"""Block manual stock issues from quarantine warehouses when the setting is enabled."""
	settings = frappe.get_doc("Inventory Tools Settings", doc.company)
	if not settings.block_issue_from_quarantine:
		return

	quarantine_warehouses = get_quarantine_warehouses(doc.company)
	if not quarantine_warehouses:
		return

	for row in doc.items:
		if row.get("s_warehouse") in quarantine_warehouses:
			# Allow transfers created via make_quarantine_release_stock_entry (carry a QI reference)
			if row.get("reference_doctype") == "Quality Inspection" and row.get("reference_name"):
				continue
			frappe.throw(
				frappe._(
					"Cannot issue stock directly from Quarantine Warehouse {0}. "
					"Release inventory via an accepted Quality Inspection."
				).format(row.s_warehouse)
			)


@frappe.whitelist()
def make_quarantine_release_stock_entry(quality_inspection_name):
	"""Create a draft Material Transfer to release stock from quarantine.

	Called from the Quality Inspection form button after the QI is accepted.
	Returns the new Stock Entry name so the browser can open it for review.
	"""
	doc = frappe.get_doc("Quality Inspection", quality_inspection_name)

	if doc.status != "Accepted" or doc.docstatus != 1:
		frappe.throw(
			frappe._("Quality Inspection must be submitted and Accepted before releasing from quarantine.")
		)

	if not doc.reference_type or not doc.reference_name:
		frappe.throw(frappe._("Quality Inspection has no reference document."))

	ref_doc = frappe.get_doc(doc.reference_type, doc.reference_name)
	settings = frappe.get_doc("Inventory Tools Settings", ref_doc.company)

	if not settings.enable_quarantine_workflow:
		frappe.throw(frappe._("Quarantine workflow is not enabled for {0}.").format(ref_doc.company))

	target_wh = None
	for row in ref_doc.items:
		if row.item_code == doc.item_code:
			target_wh = row.intended_warehouse
			break

	if not target_wh:
		frappe.throw(
			frappe._(
				"No intended warehouse found on {0} {1} for item {2}. "
				"Please create the transfer from quarantine manually."
			).format(doc.reference_type, doc.reference_name, doc.item_code)
		)

	# Use full quantity from reference doc, not sample_size (inspection sample)
	release_qty = sum(flt(row.qty) for row in ref_doc.items if row.item_code == doc.item_code)

	# actual_qty > 0 selects the warehouse where stock ARRIVED (the quarantine warehouse),
	# not the source warehouse that stock LEFT (which has a negative actual_qty entry).
	quarantine_wh = frappe.db.get_value(
		"Stock Ledger Entry",
		{
			"voucher_type": doc.reference_type,
			"voucher_no": doc.reference_name,
			"item_code": doc.item_code,
			"actual_qty": [">", 0],
		},
		"warehouse",
	)

	if not quarantine_wh:
		frappe.throw(
			frappe._(
				"Originating quarantine warehouse could not be found in the Stock Ledger "
				"for {0} {1}. Please create the transfer from quarantine manually."
			).format(doc.reference_type, doc.reference_name)
		)

	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Transfer"
	se.company = ref_doc.company

	se.append(
		"items",
		{
			"item_code": doc.item_code,
			"qty": release_qty,
			"s_warehouse": quarantine_wh,
			"t_warehouse": target_wh,
			"reference_doctype": "Quality Inspection",
			"reference_name": doc.name,
		},
	)

	se.save()
	return se.name


def handle_se_quarantine(doc, method):
	if doc.stock_entry_type != "Material Transfer for Manufacture":
		return
	settings = frappe.get_doc("Inventory Tools Settings", doc.company)

	if not settings.enable_quarantine_workflow:
		return

	for row in doc.items:
		if get_inspection_required(row.item_code, doc.company, "inspection_required_before_manufacture"):
			if not row.intended_warehouse:
				row.intended_warehouse = row.t_warehouse

			qi_template = frappe.db.get_value("Item", row.item_code, "quality_inspection_template")

			quarantine_wh = None

			if qi_template:
				quarantine_wh = frappe.db.get_value(
					"Quality Inspection Template", qi_template, "quarantine_warehouse"
				)

			quarantine_wh = quarantine_wh or settings.default_quarantine_warehouse

			if not quarantine_wh:
				frappe.throw(f"No Quarantine Warehouse configured for Item {row.item_code}")

			row.t_warehouse = quarantine_wh

			row.quality_inspection = None
