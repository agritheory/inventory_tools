import frappe
from erpnext.manufacturing.doctype.job_card.job_card import JobCard
from frappe import _, bold
from frappe.utils import get_link_to_form

from inventory_tools.inventory_tools.overrides.work_order import get_allowance_percentage


class InventoryToolsJobCard(JobCard):
	def validate_job_card(self):
		if (
			self.work_order
			and frappe.get_cached_value("Work Order", self.work_order, "status") == "Stopped"
		):
			frappe.throw(
				_("Transaction not allowed against stopped Work Order {0}").format(
					get_link_to_form("Work Order", self.work_order)
				)
			)

		if not self.time_logs:
			frappe.throw(
				_("Time logs are required for {0} {1}").format(
					bold("Job Card"), get_link_to_form("Job Card", self.name)
				)
			)

		# don't validate mfg qty so partial consumption can take place
		# PATCH: use manufacturing settings overproduction percentage to allow overproduction on Job Card
		overproduction_percentage = get_allowance_percentage(self.company, self.bom_no)
		allowed_qty = self.total_completed_qty * (1 + overproduction_percentage / 100)
		if self.for_quantity and allowed_qty <= self.for_quantity:
			total_completed_qty = frappe.bold(frappe._("Total Completed Qty"))
			qty_to_manufacture = frappe.bold(frappe._("Qty to Manufacture"))
			frappe.throw(
				frappe._("The {0} ({1}) must be equal to {2} ({3})").format(
					total_completed_qty,
					frappe.bold(self.total_completed_qty),
					qty_to_manufacture,
					frappe.bold(self.for_quantity),
				)
			)
