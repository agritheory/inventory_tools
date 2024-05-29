import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import FinishedGoodError, StockEntry
from frappe import _
from frappe.utils import flt

from inventory_tools.inventory_tools.overrides.work_order import get_allowance_percentage


class InventoryToolsStockEntry(StockEntry):
	def check_if_operations_completed(self):
		"""
		HASH: 153e0ba81b62acc170a951a289363fff5579edc7
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
		HASH: 153e0ba81b62acc170a951a289363fff5579edc7
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
				msg=_("There must be atleast 1 Finished Good in this Stock Entry").format(self.name),
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
		HASH: 153e0ba81b62acc170a951a289363fff5579edc7
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
