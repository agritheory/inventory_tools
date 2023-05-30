import datetime
import types
from itertools import groupby

import frappe
from erpnext.accounts.doctype.account.account import update_account_number
from erpnext.manufacturing.doctype.production_plan.production_plan import (
	get_items_for_material_requests,
)
from erpnext.setup.utils import enable_all_roles_and_domains, set_defaults_for_tests
from erpnext.stock.get_item_details import get_item_details
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

from beam.tests.fixtures import boms, items, operations, suppliers, workstations


def before_test():
	frappe.clear_cache()
	today = frappe.utils.getdate()
	setup_complete(
		{
			"currency": "USD",
			"full_name": "Administrator",
			"company_name": "Ambrosia Pie Company",
			"timezone": "America/New_York",
			"company_abbr": "APC",
			"domains": ["Distribution"],
			"country": "United States",
			"fy_start_date": today.replace(month=1, day=1).isoformat(),
			"fy_end_date": today.replace(month=12, day=31).isoformat(),
			"language": "english",
			"company_tagline": "Ambrosia Pie Company",
			"email": "support@agritheory.dev",
			"password": "admin",
			"chart_of_accounts": "Standard with Numbers",
			"bank_account": "Primary Checking",
		}
	)
	enable_all_roles_and_domains()
	set_defaults_for_tests()
	frappe.db.commit()
	create_test_data()
	for modu in frappe.get_all("Module Onboarding"):
		frappe.db.set_value("Module Onboarding", modu, "is_complete", 1)
	frappe.set_value("Website Settings", "Website Settings", "home_page", "login")
	frappe.db.commit()


def create_test_data():
	settings = frappe._dict(
		{
			"day": datetime.date(int(frappe.defaults.get_defaults().get("fiscal_year")), 1, 1),
			"company": frappe.defaults.get_defaults().get("company"),
			"company_account": frappe.get_value(
				"Account",
				{
					"account_type": "Bank",
					"company": frappe.defaults.get_defaults().get("company"),
					"is_group": 0,
				},
			),
		}
	)
	company_address = frappe.new_doc("Address")
	company_address.title = settings.company
	company_address.address_type = "Office"
	company_address.address_line1 = "67C Sweeny Street"
	company_address.city = "Chelsea"
	company_address.state = "MA"
	company_address.pincode = "89077"
	company_address.is_your_company_address = 1
	company_address.append("links", {"link_doctype": "Company", "link_name": settings.company})
	company_address.save()
	frappe.set_value("Company", settings.company, "tax_id", "04-1871930")
	create_warehouses(settings)
	setup_manufacturing_settings(settings)
	create_workstations()
	create_operations()
	create_item_groups(settings)
	create_suppliers(settings)
	create_items(settings)
	create_boms(settings)
	create_material_request(settings)
	# create_production_plan(settings)


def create_suppliers(settings):
	if not frappe.db.exists("Supplier Group", "Bakery"):
		bsg = frappe.new_doc("Supplier Group")
		bsg.supplier_group_name = "Bakery"
		bsg.parent_supplier_group = "All Supplier Groups"
		bsg.save()

	addresses = frappe._dict({})
	for supplier in suppliers:
		biz = frappe.new_doc("Supplier")
		biz.supplier_name = supplier[0]
		biz.supplier_group = "Bakery"
		biz.country = "United States"
		biz.supplier_default_mode_of_payment = supplier[2]
		if biz.supplier_default_mode_of_payment == "ACH/EFT":
			biz.bank = "Local Bank"
			biz.bank_account = "123456789"
		biz.currency = "USD"
		biz.default_price_list = "Standard Buying"
		biz.save()

		existing_address = frappe.get_value("Address", {"address_line1": supplier[5]["address_line1"]})
		if not existing_address:
			addr = frappe.new_doc("Address")
			addr.address_title = f"{supplier[0]} - {supplier[5]['city']}"
			addr.address_type = "Billing"
			addr.address_line1 = supplier[5]["address_line1"]
			addr.city = supplier[5]["city"]
			addr.state = supplier[5]["state"]
			addr.country = supplier[5]["country"]
			addr.pincode = supplier[5]["pincode"]
		else:
			addr = frappe.get_doc("Address", existing_address)
		addr.append("links", {"link_doctype": "Supplier", "link_name": supplier[0]})
		addr.save()


def setup_manufacturing_settings(settings):
	mfg_settings = frappe.get_doc("Manufacturing Settings", "Manufacturing Settings")
	mfg_settings.material_consumption = 1
	mfg_settings.default_wip_warehouse = "Kitchen - APC"
	mfg_settings.default_fg_warehouse = "Baked Goods - APC"
	mfg_settings.overproduction_percentage_for_work_order = 5.00
	mfg_settings.job_Card_excess_transfer = 1
	mfg_settings.save()

	if frappe.db.exists("Account", {"account_name": "Work In Progress", "company": settings.company}):
		return
	wip = frappe.new_doc("Account")
	wip.account_name = "Work in Progress"
	wip.parent_account = "1400 - Stock Assets - APC"
	wip.account_number = "1420"
	wip.company = settings.company
	wip.currency = "USD"
	wip.report_type = "Balance Sheet"
	wip.root_type = "Asset"
	wip.save()

	if frappe.db.exists("Account", {"account_name": "Work In Progress", "company": settings.company}):
		return
	wip = frappe.new_doc("Account")
	wip.account_name = "Standard Costing Reconciliation"
	wip.parent_account = "1400 - Stock Assets - APC"
	wip.account_number = "1430"
	wip.company = settings.company
	wip.currency = "USD"
	wip.report_type = "Balance Sheet"
	wip.root_type = "Asset"
	wip.save()

	frappe.set_value("Warehouse", "Kitchen - APC", "account", wip.name)


def create_workstations():
	for ws in workstations:
		if frappe.db.exists("Workstation", ws[0]):
			continue
		work = frappe.new_doc("Workstation")
		work.workstation_name = ws[0]
		work.production_capacity = ws[1]
		work.save()


def create_operations():
	for op in operations:
		if frappe.db.exists("Operation", op[0]):
			continue
		oper = frappe.new_doc("Operation")
		oper.name = op[0]
		oper.workstation = op[1]
		oper.batch_size = op[2]
		oper.description = op[3]
		oper.save()


def create_item_groups(settings):
	for ig_name in (
		"Baked Goods",
		"Bakery Supplies",
		"Ingredients",
		"Bakery Equipment",
		"Sub Assemblies",
	):
		if frappe.db.exists("Item Group", ig_name):
			continue
		ig = frappe.new_doc("Item Group")
		ig.item_group_name = ig_name
		ig.parent_item_group = "All Item Groups"
		ig.save()


def create_items(settings):
	if not frappe.db.exists("Price List", "Bakery Buying"):
		pl = frappe.new_doc("Price List")
		pl.price_list_name = "Bakery Buying"
		pl.buying = 1
		pl.append("countries", {"country": "United States"})
		pl.save()

	if not frappe.db.exists("Price List", "Bakery Wholesale"):
		pl = frappe.new_doc("Price List")
		pl.price_list_name = "Bakery Wholesale"
		pl.selling = 1
		pl.append("countries", {"country": "United States"})
		pl.save()

	if not frappe.db.exists("Pricing Rule", "Bakery Retail"):
		pr = frappe.new_doc("Pricing Rule")
		pr.title = "Bakery Retail"
		pr.selling = 1
		pr.apply_on = "Item Group"
		pr.company = settings.company
		pr.margin_type = "Percentage"
		pr.margin_rate_or_amount = 2.00
		pr.valid_from = settings.day
		pr.for_price_list = "Bakery Wholesale"
		pr.append("item_groups", {"item_group": "Baked Goods"})
		pr.save()

	for item in items:
		if frappe.db.exists("Item", item.get("item_code")):
			continue
		i = frappe.new_doc("Item")
		i.item_code = i.item_name = item.get("item_code")
		i.item_group = item.get("item_group")
		i.stock_uom = item.get("uom")
		i.description = item.get("description")
		i.maintain_stock = 1
		i.include_item_in_manufacturing = 1
		i.default_warehouse = settings.get("warehouse")
		i.default_material_request_type = (
			"Purchase" if item.get("item_group") in ("Bakery Supplies", "Ingredients") else "Manufacture"
		)
		i.valuation_method = "FIFO"
		i.is_purchase_item = 1 if item.get("item_group") in ("Bakery Supplies", "Ingredients") else 0
		i.is_sales_item = 1 if item.get("item_group") == "Baked Goods" else 0
		i.append(
			"item_defaults",
			{"company": settings.company, "default_warehouse": item.get("default_warehouse")},
		)
		if i.is_purchase_item and item.get("supplier"):
			i.append("supplier_items", {"supplier": item.get("supplier")})
		i.save()
		if item.get("item_price"):
			ip = frappe.new_doc("Item Price")
			ip.item_code = i.item_code
			ip.uom = i.stock_uom
			ip.price_list = "Bakery Wholesale" if i.is_sales_item else "Bakery Buying"
			ip.buying = 1
			ip.valid_from = "2018-1-1"
			ip.price_list_rate = item.get("item_price")
			ip.save()


def create_warehouses(settings):
	warehouses = [item.get("default_warehouse") for item in items]
	root_wh = frappe.get_value("Warehouse", {"company": settings.company, "is_group": 1})
	if frappe.db.exists("Warehouse", "Stores - APC"):
		frappe.rename_doc("Warehouse", "Stores - APC", "Storeroom - APC", force=True)
	for wh in frappe.get_all("Warehouse", {"company": settings.company}, ["name", "is_group"]):
		if wh.name not in warehouses and not wh.is_group:
			frappe.delete_doc("Warehouse", wh.name)
	for item in items:
		if frappe.db.exists("Warehouse", item.get("default_warehouse")):
			continue
		wh = frappe.new_doc("Warehouse")
		wh.warehouse_name = item.get("default_warehouse").split(" - ")[0]
		wh.parent_warehouse = root_wh
		wh.company = settings.company
		wh.save()


def create_boms(settings):
	for bom in boms[::-1]:  # reversed
		if frappe.db.exists("BOM", {"item": bom.get("item")}):
			continue
		b = frappe.new_doc("BOM")
		b.item = bom.get("item")
		b.quantity = bom.get("quantity")
		b.uom = bom.get("uom")
		b.company = settings.company
		b.rm_cost_as_per = "Price List"
		b.buying_price_list = "Bakery Buying"
		b.currency = "USD"
		b.with_operations = 1
		for item in bom.get("items"):
			b.append("items", {**item, "stock_uom": item.get("uom")})
			b.items[-1].bom_no = frappe.get_value("BOM", {"item": item.get("item_code")})
		for operation in bom.get("operations"):
			b.append("operations", {**operation, "hour_rate": 15.00})
		b.save()
		b.submit()


def create_material_request(settings):
	mr = frappe.new_doc("Material Request")
	mr.material_request_type = "Manufacture"
	mr.schedule_date = mr.transaction_date = settings.day
	mr.title = "Pies"
	mr.append(
		"items",
		{
			"item_code": "Ambrosia Pie",
			"schedule_date": mr.schedule_date,
			"qty": 40,
			"warehouse": "Baked Goods - APC",
		},
	)
	mr.append(
		"items",
		{
			"item_code": "Double Plum Pie",
			"schedule_date": mr.schedule_date,
			"qty": 40,
			"warehouse": "Baked Goods - APC",
		},
	)
	mr.append(
		"items",
		{
			"item_code": "Gooseberry Pie",
			"schedule_date": mr.schedule_date,
			"qty": 10,
			"warehouse": "Baked Goods - APC",
		},
	)
	mr.append(
		"items",
		{
			"item_code": "Kaduka Key Lime Pie",
			"schedule_date": mr.schedule_date,
			"qty": 10,
			"warehouse": "Baked Goods - APC",
		},
	)
	mr.save()
	mr.submit()


def create_production_plan(settings):
	pp = frappe.new_doc("Production Plan")
	pp.posting_date = settings.day
	pp.company = settings.company
	pp.get_items_from = "Material Request"
	pp.append(
		"material_requests",
		{
			"material_request": frappe.get_last_doc("Material Request").name,
		},
	)
	pp.combine_sub_items = 1
	pp.get_mr_items()
	for item in pp.po_items:
		item.planned_start_date = settings.day
	pp.get_sub_assembly_items()
	for item in pp.sub_assembly_items:
		item.schedule_date = settings.day
	pp.for_warehouse = "Storeroom - APC"
	raw_materials = get_items_for_material_requests(
		pp.as_dict(), warehouses=None, get_parent_warehouse_data=None
	)
	for row in raw_materials:
		pp.append(
			"mr_items",
			{
				**row,
				"warehouse": frappe.get_value(
					"Item Default", {"parent": row.get("item_code")}, "default_warehouse"
				),
			},
		)
	pp.save()
	pp.submit()

	pp.make_material_request()
	mr = frappe.get_last_doc("Material Request")
	mr.schedule_date = mr.transaction_date = settings.day
	mr.save()
	mr.submit()

	for item in mr.items:
		supplier = frappe.get_value("Item Supplier", {"parent": item.get("item_code")}, "supplier")
		item.supplier = supplier

	for supplier, _items in groupby(
		sorted((m for m in mr.items if m.supplier), key=lambda d: d.supplier),
		lambda x: x.get("supplier"),
	):
		items = list(_items)
		if not supplier:
			continue
		pr = frappe.new_doc("Purchase Receipt")
		pr.company = settings.company
		pr.supplier = supplier
		pr.posting_date = settings.day
		pr.set_posting_time = 1
		pr.buying_price_list = "Bakery Buying"
		for item in items:
			item_details = get_item_details(
				{
					"item_code": item.item_code,
					"qty": item.qty,
					"supplier": pr.supplier,
					"company": pr.company,
					"doctype": pr.doctype,
					"currency": pr.currency,
					"buying_price_list": pr.buying_price_list,
				}
			)
			pr.append("items", {**item_details})
		pr.save()
		pr.submit()

	pp.make_work_order()
	wos = frappe.get_all("Work Order", {"production_plan": pp.name})
	for wo in wos:
		wo = frappe.get_doc("Work Order", wo)
		wo.wip_warehouse = "Kitchen - APC"
		wo.save()
		wo.submit()
		job_cards = frappe.get_all("Job Card", {"work_order": wo.name})
		for job_card in job_cards:
			job_card = frappe.get_doc("Job Card", job_card)
			job_card.time_logs[0].completed_qty = wo.qty
			job_card.save()
			job_card.submit()
