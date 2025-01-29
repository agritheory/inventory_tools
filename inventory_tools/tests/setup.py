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
from frappe.utils import add_months, nowdate
from frappe.utils.data import flt, getdate

from inventory_tools.tests.fixtures import (
	boms,
	customers,
	items,
	operations,
	suppliers,
	workstations,
)


def before_test():
	frappe.clear_cache()
	setup_complete(
		{
			"currency": "USD",
			"full_name": "Administrator",
			"company_name": "Ambrosia Pie Company",
			"timezone": "America/New_York",
			"company_abbr": "APC",
			"domains": ["Distribution"],
			"country": "United States",
			"fy_start_date": getdate().replace(month=1, day=1).isoformat(),
			"fy_end_date": getdate().replace(month=12, day=31).isoformat(),
			"language": "english",
			"company_tagline": "Ambrosia Pie Company",
			"email": "support@agritheory.dev",
			"password": "admin",
			"chart_of_accounts": "Standard with Numbers",
			"bank_account": "Primary Checking",
		}
	)
	set_defaults_for_tests()
	for modu in frappe.get_all("Module Onboarding"):
		frappe.db.set_value("Module Onboarding", modu, "is_complete", 1)
	frappe.set_value("Website Settings", "Website Settings", "home_page", "login")
	frappe.db.commit()
	create_test_data()


def create_test_data():
	settings = frappe._dict(
		{
			"day": getdate().replace(month=1, day=1),
			"company": "Ambrosia Pie Company",
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
	cfc = frappe.new_doc("Company")
	cfc.company_name = "Chelsea Fruit Co"
	cfc.default_currency = "USD"
	cfc.create_chart_of_accounts_based_on = "Existing Company"
	cfc.existing_company = settings.company
	cfc.abbr = "CFC"
	cfc.save()

	frappe.db.set_single_value("Stock Settings", "valuation_method", "Moving Average")
	frappe.db.set_single_value("Stock Settings", "default_warehouse", "")
	create_warehouses(settings)
	setup_manufacturing_settings(settings)
	create_workstations()
	create_operations()
	create_item_groups(settings)
	create_price_lists(settings)
	create_suppliers(settings)
	create_customers(settings)
	create_items(settings)
	create_boms(settings)
	prod_plan_from_doc = "Sales Order"
	if prod_plan_from_doc == "Sales Order":
		create_sales_order(settings)
	else:
		create_material_request(settings)
	create_production_plan(settings, prod_plan_from_doc)
	create_fruit_material_request(settings)
	create_quotations(settings)


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
		if biz.supplier_name == "Credible Contract Baking":
			biz.append(
				"subcontracting_defaults",
				{
					"company": settings.company,
					"wip_warehouse": "Credible Contract Baking - APC",
					"return_warehouse": "Baked Goods - APC",
				},
			)
		biz.default_price_list = "Bakery Buying"
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


def create_customers(settings):
	for customer_name in customers:
		customer = frappe.new_doc("Customer")
		customer.customer_name = customer_name
		customer.customer_group = "Commercial"
		customer.customer_type = "Company"
		customer.territory = "United States"
		customer.save()


def setup_manufacturing_settings(settings):
	mfg_settings = frappe.get_doc("Manufacturing Settings", "Manufacturing Settings")
	mfg_settings.material_consumption = 1
	mfg_settings.default_wip_warehouse = "Kitchen - APC"
	mfg_settings.default_fg_warehouse = "Refrigerated Display - APC"
	mfg_settings.overproduction_percentage_for_work_order = 5.00
	mfg_settings.job_card_excess_transfer = 1
	mfg_settings.save()

	if not frappe.db.exists(
		"Account", {"account_name": "Work In Progress", "company": settings.company}
	):
		wip = frappe.new_doc("Account")
		wip.account_name = "Work in Progress"
		wip.parent_account = "1400 - Stock Assets - APC"
		wip.account_number = "1420"
		wip.company = settings.company
		wip.currency = "USD"
		wip.report_type = "Balance Sheet"
		wip.root_type = "Asset"
		wip.save()

	frappe.set_value("Warehouse", "Kitchen - APC", "account", wip.name)
	frappe.set_value(
		"Inventory Tools Settings", settings.company, "enable_work_order_subcontracting", 1
	)
	frappe.set_value("Inventory Tools Settings", settings.company, "create_purchase_orders", 0)
	frappe.set_value(
		"Inventory Tools Settings", settings.company, "overproduction_percentage_for_work_order", 50
	)


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
		if len(op) == 5:
			for aw in op[4]:
				oper.append(
					"alternative_workstations",
					{
						"workstation": aw,
					},
				)
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


def create_price_lists(settings):
	if not frappe.db.exists("Price List", "Bakery Buying"):
		pl = frappe.new_doc("Price List")
		pl.price_list_name = "Bakery Buying"
		pl.currency = "USD"
		pl.buying = 1
		pl.append("countries", {"country": "United States"})
		pl.save()

	if not frappe.db.exists("Price List", "Bakery Wholesale"):
		pl = frappe.new_doc("Price List")
		pl.price_list_name = "Bakery Wholesale"
		pl.currency = "USD"
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
		pr.currency = "USD"
		pr.append("item_groups", {"item_group": "Baked Goods"})
		pr.save()


def create_items(settings):
	for item in items:
		if frappe.db.exists("Item", item.get("item_code")):
			continue
		i = frappe.new_doc("Item")
		i.item_code = i.item_name = item.get("item_code")
		i.item_group = item.get("item_group")
		i.stock_uom = item.get("uom")
		i.description = item.get("description")
		i.is_stock_item = 0 if item.get("is_stock_item") == 0 else 1
		i.include_item_in_manufacturing = 1
		i.valuation_rate = item.get("valuation_rate") or 0
		i.is_sub_contracted_item = item.get("is_sub_contracted_item") or 0
		i.default_warehouse = settings.get("warehouse")
		i.default_material_request_type = (
			"Purchase"
			if item.get("item_group") in ("Bakery Supplies", "Ingredients")
			or item.get("is_sub_contracted_item")
			else "Manufacture"
		)
		i.valuation_method = "Moving Average"
		if item.get("uom_conversion_detail"):
			for uom, cf in item.get("uom_conversion_detail").items():
				i.append("uoms", {"uom": uom, "conversion_factor": cf})
		i.is_purchase_item = (
			1
			if item.get("item_group") in ("Bakery Supplies", "Ingredients")
			or item.get("is_sub_contracted_item")
			else 0
		)
		i.is_sales_item = 1 if item.get("item_group") == "Baked Goods" else 0
		i.append(
			"item_defaults",
			{
				"company": settings.company,
				"default_warehouse": item.get("default_warehouse"),
				"default_supplier": item.get("default_supplier"),
				"requires_rfq": True if item.get("item_code") == "Cloudberry" else False,
			},
		)
		if i.is_purchase_item and item.get("supplier"):
			if isinstance(item.get("supplier"), list):
				[i.append("supplier_items", {"supplier": s}) for s in item.get("supplier")]
			else:
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
		if item.get("available_in_house"):
			se = frappe.new_doc("Stock Entry")
			se.posting_date = settings.day
			se.set_posting_time = 1
			se.stock_entry_type = "Material Receipt"
			se.append(
				"items",
				{
					"item_code": item.get("item_code"),
					"t_warehouse": item.get("default_warehouse"),
					"qty": item.get("opening_qty"),
					"uom": item.get("uom"),
					"stock_uom": item.get("uom"),
					"conversion_factor": 1,
					"basic_rate": item.get("item_price"),
					"expense_account": "1910 - Temporary Opening - APC",
				},
			)
			se.save()
			se.submit()


def create_warehouses(settings):
	inventory_tools_settings = frappe.get_doc("Inventory Tools Settings", settings.company)
	inventory_tools_settings.enable_work_order_subcontracting = 1
	inventory_tools_settings.create_purchase_orders = 0
	inventory_tools_settings.update_warehouse_path = 1
	inventory_tools_settings.save()

	warehouses = [item.get("default_warehouse") for item in items]
	root_wh = frappe.get_value("Warehouse", {"company": settings.company, "is_group": 1})
	if frappe.db.exists("Warehouse", "Stores - APC"):
		frappe.rename_doc("Warehouse", "Stores - APC", "Storeroom - APC", force=True)
	if frappe.db.exists("Warehouse", "Finished Goods - APC"):
		frappe.rename_doc("Warehouse", "Finished Goods - APC", "Baked Goods - APC", force=True)
		frappe.set_value("Warehouse", "Baked Goods - APC", "is_group", 1)
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

	wh = frappe.new_doc("Warehouse")
	wh.warehouse_name = "Bakery Display"
	wh.parent_warehouse = "Baked Goods - APC"
	wh.company = settings.company
	wh.save()

	wh = frappe.get_doc("Warehouse", "Refrigerated Display - APC")
	wh.parent_warehouse = "Baked Goods - APC"
	wh.save()


def create_boms(settings):
	for bom in boms[::-1]:  # reversed
		if frappe.db.exists("BOM", {"item": bom.get("item")}) and bom.get("item") != "Pie Crust":
			continue
		b = frappe.new_doc("BOM")
		b.item = bom.get("item")
		b.quantity = bom.get("quantity")
		b.uom = bom.get("uom")
		b.company = settings.company
		b.is_default = 0 if bom.get("is_default") == 0 else 1
		b.is_subcontracted = bom.get("is_subcontracted") or 0
		b.overproduction_percentage_for_work_order = bom.get(
			"overproduction_percentage_for_work_order", None
		)
		b.rm_cost_as_per = "Price List"
		b.buying_price_list = "Bakery Buying"
		b.currency = "USD"
		b.with_operations = 0 if bom.get("with_operations") == 0 else 1
		for item in bom.get("items"):
			b.append("items", {**item, "stock_uom": item.get("uom")})
			b.items[-1].bom_no = frappe.get_value("BOM", {"item": item.get("item_code")})
		for operation in bom.get("operations"):
			b.append("operations", {**operation, "hour_rate": 15.00})
		b.save()
		b.submit()


def create_sales_order(settings):
	so = frappe.new_doc("Sales Order")
	so.transaction_date = settings.day
	so.customer = customers[0]
	so.order_type = "Sales"
	so.currency = "USD"
	so.selling_price_list = "Bakery Wholesale"
	so.append(
		"items",
		{
			"item_code": "Ambrosia Pie",
			"delivery_date": so.transaction_date,
			"qty": 30,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	so.append(
		"items",
		{
			"item_code": "Double Plum Pie",
			"delivery_date": so.transaction_date,
			"qty": 30,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	so.append(
		"items",
		{
			"item_code": "Gooseberry Pie",
			"delivery_date": so.transaction_date,
			"qty": 10,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	so.append(
		"items",
		{
			"item_code": "Kaduka Key Lime Pie",
			"delivery_date": so.transaction_date,
			"qty": 10,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	so.append(
		"items",
		{
			"item_code": "Pocketful of Bay",
			"delivery_date": so.transaction_date,
			"qty": 10,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	so.append(
		"items",
		{
			"item_code": "Tower of Bay-bel",
			"delivery_date": so.transaction_date,
			"qty": 20,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	so.save()
	so.submit()


def create_material_request(settings):
	mr = frappe.new_doc("Material Request")
	mr.material_request_type = "Manufacture"
	mr.schedule_date = mr.transaction_date = settings.day
	mr.title = "Pies"
	mr.company = settings.company
	mr.append(
		"items",
		{
			"item_code": "Ambrosia Pie",
			"schedule_date": mr.schedule_date,
			"qty": 40,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	mr.append(
		"items",
		{
			"item_code": "Double Plum Pie",
			"schedule_date": mr.schedule_date,
			"qty": 40,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	mr.append(
		"items",
		{
			"item_code": "Gooseberry Pie",
			"schedule_date": mr.schedule_date,
			"qty": 10,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	mr.append(
		"items",
		{
			"item_code": "Kaduka Key Lime Pie",
			"schedule_date": mr.schedule_date,
			"qty": 10,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	mr.append(
		"items",
		{
			"item_code": "Pocketful of Bay",
			"delivery_date": mr.schedule_date,
			"qty": 10,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	mr.append(
		"items",
		{
			"item_code": "Tower of Bay-bel",
			"delivery_date": mr.schedule_date,
			"qty": 20,
			"warehouse": "Refrigerated Display - APC",
		},
	)
	mr.save()
	mr.submit()
	mr = frappe.new_doc("Material Request")
	mr.material_request_type = "Purchase"
	mr.schedule_date = mr.transaction_date = settings.day
	mr.title = "Boxes"
	mr.company = settings.company


def create_production_plan(settings, prod_plan_from_doc):
	pp = frappe.new_doc("Production Plan")
	pp.posting_date = settings.day
	pp.company = settings.company
	pp.combine_sub_items = 1
	if prod_plan_from_doc == "Sales Order":
		pp.get_items_from = "Sales Order"
		pp.append(
			"sales_orders",
			{
				"sales_order": frappe.get_last_doc("Sales Order").name,
			},
		)
		pp.get_items()
	else:
		pp.get_items_from = "Material Request"
		pp.append(
			"material_requests",
			{
				"material_request": frappe.get_last_doc("Material Request").name,
			},
		)
		pp.get_mr_items()
	for item in pp.po_items:
		item.planned_start_date = settings.day
	pp.get_sub_assembly_items()
	for item in pp.sub_assembly_items:
		item.schedule_date = settings.day
		if item.production_item == "Pie Crust":
			idx = item.idx
			item.type_of_manufacturing = "Subcontract"
			item.supplier = "Credible Contract Baking"
			item.qty = 50
	pp.append("sub_assembly_items", pp.sub_assembly_items[idx - 1].as_dict())
	pp.sub_assembly_items[-1].name = None
	pp.sub_assembly_items[-1].type_of_manufacturing = "In House"
	pp.sub_assembly_items[-1].bom_no = "BOM-Pie Crust-001"
	pp.sub_assembly_items[-1].supplier = None
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
	mr.company = settings.company
	mr.save()
	mr.submit()

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
			job_card.submit()  # don't submit to test alternative workstations


def create_fruit_material_request(settings):
	fruits = [
		"Bayberry",
		"Cocoplum",
		"Damson Plum",
		"Gooseberry",
		"Hairless Rambutan",
		"Kaduka Lime",
		"Limequat",
		"Tayberry",
	]

	for fruit in fruits:
		i = frappe.get_doc("Item", fruit)
		i.append(
			"item_defaults",
			{
				"company": "Chelsea Fruit Co",
				"default_warehouse": "Stores - CFC",
				"default_supplier": "Southern Fruit Supply",
			},
		)
		i.save()
		ip = frappe.copy_doc(frappe.get_doc("Item Price", {"item_code": fruit}))
		ip.price_list = "Standard Buying"
		ip.price_list_rate = flt(ip.price_list_rate * 0.75, 2)
		ip.save()

	mr = frappe.new_doc("Material Request")
	mr.company = "Chelsea Fruit Co"
	mr.transaction_date = settings.day
	mr.schedule_date = getdate()
	mr.purpose = "Purchase"
	for f in fruits:
		mr.append(
			"items",
			{
				"item_code": f,
				"qty": 100,
				"schedule_date": mr.schedule_date,
				"warehouse": "Stores - CFC",
				"uom": "Pound",
			},
		)
	mr.save()
	mr.submit()


def create_quotations(settings):
	quotation = frappe.new_doc("Quotation")

	items = ["Ambrosia Pie", "Gooseberry Pie", "Double Plum Pie"]
	for item in items:
		i = frappe.get_doc("Item", item)
		i.append(
			"item_defaults",
			{
				"company": "Chelsea Fruit Co",
				"default_warehouse": "Finished Goods - CFC",
			},
		)
		i.save()

	values = {
		"quotation_to": "Customer",
		"order_type": "Sales",
		"party_name": "Almacs Food Group",
		"selling_price_list": "Bakery Wholesale",
		"currency": "USD",
		"conversion_rate": 1,
		"transaction_date": nowdate(),
		"valid_till": add_months(nowdate(), 1),
		"items": [{"item_code": "Ambrosia Pie", "qty": 1}, {"item_code": "Gooseberry Pie", "qty": 5}],
		"company": settings.company,
	}
	quotation.update(values)
	quotation.save()
	quotation.submit()

	quotation = frappe.new_doc("Quotation")
	values = {
		"quotation_to": "Customer",
		"order_type": "Sales",
		"party_name": "Almacs Food Group",
		"selling_price_list": "Bakery Wholesale",
		"currency": "USD",
		"conversion_rate": 1,
		"transaction_date": nowdate(),
		"valid_till": add_months(nowdate(), 1),
		"items": [{"item_code": "Ambrosia Pie", "qty": 1}, {"item_code": "Gooseberry Pie", "qty": 5}],
		"company": settings.company,
	}
	quotation.update(values)
	quotation.save()
	quotation.submit()

	quotation = frappe.new_doc("Quotation")
	values = {
		"quotation_to": "Customer",
		"order_type": "Sales",
		"party_name": "Downtown Deli",
		"selling_price_list": "Bakery Wholesale",
		"currency": "USD",
		"conversion_rate": 1,
		"transaction_date": nowdate(),
		"valid_till": add_months(nowdate(), 1),
		"items": [{"item_code": "Ambrosia Pie", "qty": 2}, {"item_code": "Double Plum Pie", "qty": 1}],
		"company": settings.company,
	}
	quotation.update(values)
	quotation.save()
	quotation.submit()

	quotation = frappe.new_doc("Quotation")
	values = {
		"quotation_to": "Customer",
		"order_type": "Sales",
		"party_name": "Almacs Food Group",
		"selling_price_list": "Bakery Wholesale",
		"currency": "USD",
		"conversion_rate": 1,
		"transaction_date": nowdate(),
		"valid_till": add_months(nowdate(), 1),
		"items": [{"item_code": "Ambrosia Pie", "qty": 5}, {"item_code": "Double Plum Pie", "qty": 10}],
		"company": "Chelsea Fruit Co",
	}
	quotation.update(values)
	quotation.save()
	quotation.submit()
