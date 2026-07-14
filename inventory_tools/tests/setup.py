# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import datetime
import shutil
from pathlib import Path

import frappe
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from erpnext.manufacturing.doctype.production_plan.production_plan import (
	get_items_for_material_requests,
)
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from test_utils.utils.setup_fixtures import create_quarantine_warehouse
from erpnext.setup.utils import set_defaults_for_tests
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
from frappe.utils.data import add_months, flt, getdate, nowdate, get_datetime
from webshop.webshop.doctype.website_item.website_item import make_website_item
from inventory_tools.tests.fixtures import (
	operations,
	suppliers,
	workstations,
)


def read_json(name):
	fixtures_dir = Path(frappe.get_app_path("inventory_tools", "tests", "fixtures"))
	return frappe.get_file_json(fixtures_dir / f"{name}.json")


BOMS = read_json("boms")
CUSTOMERS = read_json("customers")
ITEM_DIMENSIONS = read_json("item_dimensions")
ITEMS = read_json("items")
ITEMS_STOCKENTRY = read_json("items_stockentry")
SPECIFICATIONS = read_json("specifications")
WAREHOUSE_DIMENSIONS = read_json("warehouse_dimensions")
WAREHOUSE_LOCATIONS = read_json("warehouse_locations")
WAREHOUSE_PLAN_MATRIX = str(read_json("warehouse_plan_matrix"))


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

	if not frappe.db.exists("Company", "Chelsea Fruit Co"):
		cfc = frappe.new_doc("Company")
		cfc.company_name = "Chelsea Fruit Co"
		cfc.default_currency = "USD"
		cfc.create_chart_of_accounts_based_on = "Existing Company"
		cfc.existing_company = settings.company
		cfc.abbr = "CFC"
		cfc.save()
	else:
		cfc = frappe.get_doc("Company", "Chelsea Fruit Co")

	copy_image_fixtures()
	frappe.db.set_single_value("Stock Settings", "valuation_method", "Moving Average")
	frappe.db.set_single_value("Stock Settings", "default_warehouse", "")
	create_warehouse_plan(cfc)
	create_warehouses(settings)
	create_warehouse_locations()
	setup_manufacturing_settings(settings)
	create_item_groups(settings)
	create_price_lists(settings)
	create_suppliers(settings)
	create_customers(settings)
	create_items(settings)
	create_workstations(settings)
	create_operations()
	create_boms(settings)
	prod_plan_from_doc = "Sales Order"
	if prod_plan_from_doc == "Sales Order":
		create_sales_order(settings)
	else:
		create_material_request(settings)
	create_production_plan(settings, prod_plan_from_doc)
	create_fruit_material_request(settings)
	create_quotations(settings)
	create_specifications(settings)
	create_item_dimensions()
	create_warehouse_dimensions()
	create_stock_entries()
	create_sales_order_2()


def copy_image_fixtures():
	fixtures_dir = Path(frappe.get_app_path("inventory_tools", "tests", "fixtures"))
	for path in fixtures_dir.iterdir():
		if path.is_file() and path.suffix in (".png", ".jpg", ".jpeg"):
			public_file_path = Path(frappe.get_site_path("public", "files", path.name))
			shutil.copy(path.resolve(), public_file_path.resolve())


def create_suppliers(settings):
	if not frappe.db.exists("Supplier Group", "Bakery"):
		bsg = frappe.new_doc("Supplier Group")
		bsg.supplier_group_name = "Bakery"
		bsg.parent_supplier_group = "All Supplier Groups"
		bsg.save()

	addresses = frappe._dict({})
	for supplier in suppliers:
		biz = frappe.new_doc("Supplier")
		biz.supplier_name = supplier["name"]
		biz.supplier_group = "Bakery"
		biz.country = "United States"
		biz.supplier_default_mode_of_payment = supplier.get("payment_mode")
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
					"return_warehouse": "Refrigerated Display - APC",
				},
			)
		biz.default_price_list = "Bakery Buying"
		biz.save()

		address_data = supplier.get("address", {})
		existing_address = frappe.get_value(
			"Address", {"address_line1": address_data.get("address_line1")}
		)
		if not existing_address:
			addr = frappe.new_doc("Address")
			addr.address_title = f"{supplier['name']} - {address_data.get('city')}"
			addr.address_type = "Billing"
			addr.address_line1 = address_data.get("address_line1")
			addr.city = address_data.get("city")
			addr.state = address_data.get("state")
			addr.country = address_data.get("country")
			addr.pincode = address_data.get("pincode")
		else:
			addr = frappe.get_doc("Address", existing_address)
		addr.append("links", {"link_doctype": "Supplier", "link_name": supplier["name"]})
		addr.save()


def create_customers(settings):
	for customer_name in CUSTOMERS:
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

	if not frappe.db.exists(
		"Account", {"account_name": "Accrued Manufacturing Wages", "company": settings.company}
	):
		wip = frappe.new_doc("Account")
		wip.account_name = "Accrued Manufacturing Wages"
		wip.parent_account = "2200 - Stock Liabilities - APC"
		wip.account_number = "2212"
		wip.company = settings.company
		wip.currency = "USD"
		wip.report_type = "Balance Sheet"
		wip.root_type = "Liability"
		wip.account_type = "Expenses Included In Valuation"
		wip.save()

	if not frappe.db.exists(
		"Account", {"account_name": "Accrued Manufacturing Electricity", "company": settings.company}
	):
		wip = frappe.new_doc("Account")
		wip.account_name = "Accrued Manufacturing Electricity"
		wip.parent_account = "2200 - Stock Liabilities - APC"
		wip.account_number = "2213"
		wip.company = settings.company
		wip.currency = "USD"
		wip.report_type = "Balance Sheet"
		wip.root_type = "Liability"
		wip.account_type = "Expenses Included In Valuation"
		wip.save()

	if not frappe.db.exists(
		"Account",
		{"account_name": "Accrued Manufacturing Rent Contribution", "company": settings.company},
	):
		wip = frappe.new_doc("Account")
		wip.account_name = "Accrued Manufacturing Rent Contribution"
		wip.parent_account = "2200 - Stock Liabilities - APC"
		wip.account_number = "2214"
		wip.company = settings.company
		wip.currency = "USD"
		wip.report_type = "Balance Sheet"
		wip.root_type = "Liability"
		wip.account_type = "Expenses Included In Valuation"
		wip.save()

	if not frappe.db.exists(
		"Account", {"account_name": "Manufacturing Wages Capitalized", "company": settings.company}
	):
		wip = frappe.new_doc("Account")
		wip.account_name = "Manufacturing Wages Capitalized"
		wip.parent_account = "5110 - Stock Expenses - APC"
		wip.account_number = "5120"
		wip.company = settings.company
		wip.currency = "USD"
		wip.report_type = "Profit and Loss"
		wip.root_type = "Expense"
		wip.save()

	frappe.set_value(
		"Inventory Tools Settings", settings.company, "enable_work_order_subcontracting", 1
	)
	frappe.set_value("Inventory Tools Settings", settings.company, "create_purchase_orders", 0)
	frappe.set_value(
		"Inventory Tools Settings",
		settings.company,
		"allow_alternative_workstations",
		"Allow Manually Defined Alternative Workstations",
	)
	frappe.set_value("Inventory Tools Settings", settings.company, "create_purchase_orders", 0)
	frappe.set_value(
		"Inventory Tools Settings", settings.company, "overproduction_percentage_for_work_order", 50
	)
	frappe.set_value("Inventory Tools Settings", settings.company, "show_on_website", 1)
	frappe.set_value("Inventory Tools Settings", settings.company, "show_in_listview", 1)


def create_workstations(settings):
	if not frappe.db.exists("Plant Floor", "Kitchen"):
		pf = frappe.new_doc("Plant Floor")
		pf.floor_name = "Kitchen"
		pf.company = settings.company
		pf.warehouse = "Kitchen - APC"
		pf.plant_floor_layout = "/files/floor_plan.png"
		pf.save()

	for ws in workstations:
		if not frappe.db.exists("Workstation Type", ws.get("workstation_type")):
			wst = frappe.new_doc("Workstation Type")
			wst.workstation_type = ws.get("workstation_type")
			wst.save()

		if frappe.db.exists("Workstation", ws.get("name")):
			work = frappe.get_doc("Workstation", ws.get("name"))
		else:
			work = frappe.new_doc("Workstation")

		work.workstation_name = ws.get("name")
		work.production_capacity = ws.get("hour_rate")
		work.hour_rate = ws.get("hour_rate")
		work.workstation_type = ws.get("workstation_type")
		work.plant_floor = "Kitchen"
		work.off_status_image = ws.get("off_status_image")
		work.on_status_image = ws.get("on_status_image")
		for oc in ws.get("operating_costs"):
			if oc.get("electricity_cost"):
				work.append(
					"workstation_operating_cost",
					{
						"from_date": oc.get("from_date"),
						"to_date": oc.get("to_date"),
						"account": "2213 - Accrued Manufacturing Electricity - APC",
						"item_code": "Electricity",
						"qty": oc.get("electricity_cost"),
					},
				)

			if oc.get("rent_cost"):
				work.append(
					"workstation_operating_cost",
					{
						"from_date": oc.get("from_date"),
						"to_date": oc.get("to_date"),
						"account": "2214 - Accrued Manufacturing Rent Contribution - APC",
						"item_code": "Rent",
						"qty": oc.get("rent_cost"),
					},
				)

			if oc.get("wages"):
				work.append(
					"workstation_operating_cost",
					{
						"from_date": oc.get("from_date"),
						"to_date": oc.get("to_date"),
						"account": "2212 - Accrued Manufacturing Wages - APC",
						"item_code": None,
						"qty": oc.get("wages"),
					},
				)

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

	if not frappe.db.exists("Brand", "Ambrosia Pie Co"):
		brand = frappe.new_doc("Brand")
		brand.brand = "Ambrosia Pie Co"
		brand.save()


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
	for item in ITEMS:
		if frappe.db.exists("Item", item.get("item_code")):
			continue
		i = frappe.new_doc("Item")
		i.item_code = i.item_name = item.get("item_code")
		i.item_group = item.get("item_group")
		i.stock_uom = item.get("uom")
		i.description = item.get("description")
		i.is_stock_item = 0 if item.get("is_stock_item") == 0 else 1
		i.include_item_in_manufacturing = 0 if item.get("is_stock_item") == 0 else 1
		i.valuation_rate = item.get("valuation_rate") or 0
		i.is_sub_contracted_item = item.get("is_sub_contracted_item") or 0
		i.default_warehouse = item.get("default_warehouse") or settings.get("warehouse")
		i.default_supplier = item.get("default_supplier")
		i.weight_uom = item.get("weight_uom") if i.is_stock_item else None
		i.weight_per_unit = item.get("weight_per_unit")
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
		if item.get("item_group") == "Baked Goods":
			i.is_sales_item = 1
			i.sales_uom = "Nos"
		elif item.get("item_group") == "Ingredients":
			i.is_sales_item = 1
			i.sales_uom = "Pound"
		else:
			i.is_sales_item = 0
			i.sales_uom = None

		i.shelf_life_in_days = 7 if i.is_sales_item else None
		i.brand = "Ambrosia Pie Co" if i.is_sales_item else None
		i.append(
			"item_defaults",
			{
				"company": settings.company,
				"default_warehouse": i.default_warehouse,
				"default_supplier": i.default_supplier,
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

			if i.is_sales_item:
				ip = frappe.new_doc("Item Price")
				ip.item_code = i.item_code
				ip.uom = i.stock_uom
				ip.price_list = "Bakery Buying"
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
		if i.is_sales_item:
			website_item = make_website_item(i, True)
			website_item = frappe.get_doc("Website Item", website_item[0])
			website_item.route = f"products/{frappe.scrub(i.name)}"
			website_item.save()


def create_warehouse_plan(cfc):
	if frappe.db.exists("Warehouse Plan", "All Warehouses - CFC"):
		return
	warehouse_plan = frappe.new_doc("Warehouse Plan")
	warehouse_plan.update(
		{
			"company": cfc.name,
			"horizontal": 50,
			"vertical": 32,
			"uom": "Meter",
			"offset": "1,1,2.2,1",
			"floor_plan": "/files/warehouse_plan.png",
			"group_warehouse": "All Warehouses - CFC",
			"matrix": WAREHOUSE_PLAN_MATRIX,
			"pickup_point_x": 0,
			"pickup_point_y": 9,
		}
	)
	warehouse_plan.save()


def create_warehouses(settings):
	inventory_tools_settings = frappe.get_doc("Inventory Tools Settings", settings.company)
	inventory_tools_settings.enable_work_order_subcontracting = 1
	inventory_tools_settings.create_purchase_orders = 0
	inventory_tools_settings.update_warehouse_path = 1
	inventory_tools_settings.save()

	warehouses = [item.get("default_warehouse") for item in ITEMS]
	root_wh = frappe.get_value("Warehouse", {"company": settings.company, "is_group": 1})
	if frappe.db.exists("Warehouse", "Stores - APC"):
		frappe.rename_doc("Warehouse", "Stores - APC", "Storeroom - APC", force=True)
	if frappe.db.exists("Warehouse", "Finished Goods - APC"):
		frappe.rename_doc("Warehouse", "Finished Goods - APC", "Baked Goods - APC", force=True)
		frappe.set_value("Warehouse", "Baked Goods - APC", "is_group", 1)
	for wh in frappe.get_all("Warehouse", {"company": settings.company}, ["name", "is_group"]):
		if wh.name not in warehouses and not wh.is_group:
			frappe.delete_doc("Warehouse", wh.name)
	for item in ITEMS:
		if item.get("is_stock_item") == 0:
			continue
		if frappe.db.exists("Warehouse", item.get("default_warehouse")):
			continue
		wh = frappe.new_doc("Warehouse")
		wh.warehouse_name = item.get("default_warehouse").split(" - ")[0]
		wh.parent_warehouse = root_wh
		wh.company = settings.company
		wh.save()

	if not frappe.db.exists("Warehouse", {"warehouse_name": "Bakery Display"}):
		wh = frappe.new_doc("Warehouse")
		wh.warehouse_name = "Bakery Display"
		wh.parent_warehouse = "Baked Goods - APC"
		wh.company = settings.company
		wh.save()

	if not frappe.db.exists("Warehouse", {"warehouse_name": "Refrigerated Display - APC"}):
		wh = frappe.get_doc("Warehouse", "Refrigerated Display - APC")
		wh.parent_warehouse = "Baked Goods - APC"
		wh.save()

	if not frappe.db.exists("Warehouse", {"warehouse_name": "Credible Contract Baking"}):
		wh = frappe.new_doc("Warehouse")
		wh.warehouse_name = "Credible Contract Baking - APC"
		wh.parent_warehouse = "All Warehouses - APC"
		wh.company = settings.company
		wh.save()


def create_warehouse_locations():
	for details in WAREHOUSE_LOCATIONS:
		warehouse = frappe.new_doc("Warehouse")
		warehouse.update(details)
		warehouse.save()


def create_quarantine_quality_control_data(settings):
	"""Quarantine warehouses, QC templates, item config for quarantine quality control tests."""
	for company in [settings.company, "Chelsea Fruit Co"]:
		if not frappe.db.get_value("Inventory Tools Settings", company, "default_quarantine_warehouse"):
			create_quarantine_warehouse(
				settings=frappe._dict({"company": company}),
				wh_name="Quarantine",
				is_default_scrap_wh=False,
			)

	if not frappe.db.exists("Quality Inspection Parameter", "Weight"):
		frappe.get_doc(
			{"doctype": "Quality Inspection Parameter", "parameter": "Weight", "description": "Weight"}
		).insert()

	if not frappe.db.exists("Quality Inspection Template", "Fruit QC"):
		qit = frappe.new_doc("Quality Inspection Template")
		qit.quality_inspection_template_name = "Fruit QC"
		qit.quarantine_warehouse = "Quarantine - CFC"
		qit.append(
			"item_quality_inspection_parameter",
			{"specification": "Weight", "numeric": 1, "min_value": 0, "max_value": 100},
		)
		qit.insert()

	if not frappe.db.exists("Quality Inspection Template", "Ingredient QC"):
		qit = frappe.new_doc("Quality Inspection Template")
		qit.quality_inspection_template_name = "Ingredient QC"
		qit.quarantine_warehouse = "Quarantine - APC"
		qit.append(
			"item_quality_inspection_parameter",
			{"specification": "Weight", "numeric": 1, "min_value": 0, "max_value": 100},
		)
		qit.insert()

	bayberry = frappe.get_doc("Item", "Bayberry")
	bayberry.quality_inspection_template = "Fruit QC"
	bayberry.save()
	item_defaults = [d for d in bayberry.item_defaults if d.company == "Chelsea Fruit Co"]
	if item_defaults:
		item_defaults[0].inspection_required_before_purchase = 1
	else:
		bayberry.append(
			"item_defaults",
			{
				"company": "Chelsea Fruit Co",
				"default_warehouse": "Stores - CFC",
				"default_supplier": "Southern Fruit Supply",
				"inspection_required_before_purchase": 1,
			},
		)
	bayberry.save()

	for company, wh in [
		("Chelsea Fruit Co", "Quarantine - CFC"),
		(settings.company, "Quarantine - APC"),
	]:
		settings_doc = frappe.get_doc("Inventory Tools Settings", company)
		settings_doc.default_quarantine_warehouse = wh
		settings_doc.enable_quarantine_workflow = 0
		settings_doc.save()

	frappe.db.commit()
	receive_qc_workflow()


def receive_qc_workflow():
	"""PO (Bayberry only) -> PR (quarantine) -> QI (release). Satisfies Bayberry before material demand tests."""
	mr_names = frappe.get_all(
		"Material Request",
		filters={"company": "Chelsea Fruit Co", "docstatus": 1},
		pluck="name",
	)
	fruit_mr_name = None
	bayberry_mri = None
	for name in mr_names:
		bayberry_mri = frappe.db.get_value(
			"Material Request Item",
			{"parent": name, "item_code": "Bayberry"},
			"name",
		)
		if bayberry_mri:
			fruit_mr_name = name
			break
	if not fruit_mr_name or not bayberry_mri:
		return
	mr = frappe.get_doc("Material Request", fruit_mr_name)
	bayberry_row = next((r for r in mr.items if r.item_code == "Bayberry"), None)
	if (
		not bayberry_row
		or bayberry_row.received_qty >= bayberry_row.stock_qty
		or bayberry_row.ordered_qty >= bayberry_row.stock_qty
	):
		return

	# PO for Bayberry only (minimal change vs material demand tests)
	po = make_purchase_order(
		fruit_mr_name, target_doc=None, args={"filtered_children": [bayberry_mri]}
	)
	po.supplier = "Southern Fruit Supply"
	po.buying_price_list = "Bakery Buying"

	if not po.items:
		return

	po.save()
	po.submit()

	cfc_settings = frappe.get_doc("Inventory Tools Settings", "Chelsea Fruit Co")
	cfc_settings.enable_quarantine_workflow = 1
	cfc_settings.save()

	pr = make_purchase_receipt(po.name)
	pr.submit()

	qa = frappe.new_doc("Quality Inspection")
	qa.report_date = getdate()
	qa.inspection_type = "Incoming"
	qa.reference_type = "Purchase Receipt"
	qa.reference_name = pr.name
	qa.item_code = "Bayberry"
	qa.sample_size = 5
	qa.quality_inspection_template = "Fruit QC"
	qa.inspected_by = frappe.session.user
	qa.status = "Accepted"
	qa.append(
		"readings",
		{"specification": "Weight", "min_value": 0, "max_value": 100, "reading_1": "50"},
	)
	qa.save()
	qa.submit()

	cfc_settings.enable_quarantine_workflow = 0
	cfc_settings.save()


def create_boms(settings):
	for bom in BOMS[::-1]:  # reversed
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
	so.customer = CUSTOMERS[0]
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


def create_sales_order_2():
	so = frappe.new_doc("Sales Order")
	so.transaction_date = getdate().replace(month=1, day=1)
	so.delivery_date = getdate().replace(month=1, day=3)
	so.customer = "Whole Harvest Grocery Group"
	so.company = "Chelsea Fruit Co"
	so.append(
		"items",
		{
			"item_code": "Bayberry",
			"qty": 20,
			"delivery_date": getdate().replace(month=1, day=3),
			"warehouse": "All Warehouses - CFC",
		},
	)
	so.append(
		"items",
		{
			"item_code": "Kepel",
			"qty": 12,
			"delivery_date": getdate().replace(month=1, day=3),
			"warehouse": "All Warehouses - CFC",
		},
	)
	so.append(
		"items",
		{
			"item_code": "Lychee",
			"qty": 3,
			"delivery_date": getdate().replace(month=1, day=3),
			"warehouse": "All Warehouses - CFC",
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
	pp.skip_available_sub_assembly_item = 0
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
		# Set supplier on subcontracted Work Order (uses BOM with is_subcontracted=1)
		if wo.bom_no and frappe.db.get_value("BOM", wo.bom_no, "is_subcontracted"):
			wo.supplier = "Credible Contract Baking"
		wo.save()
		wo.submit()
		job_cards = frappe.get_all("Job Card", {"work_order": wo.name})
		start_time = get_datetime()
		for job_card in job_cards:
			job_card = frappe.get_doc("Job Card", job_card)
			batch_size, total_operation_time = frappe.get_value(
				"Operation", job_card.operation, ["batch_size", "total_operation_time"]
			)
			time_in_mins = (total_operation_time / batch_size) * wo.qty
			job_card.append(
				"time_logs",
				{
					"completed_qty": wo.qty,
					"from_time": start_time,
					"to_time": start_time + datetime.timedelta(minutes=time_in_mins),
					"time_in_mins": time_in_mins,
				},
			)

	# Create and submit a subcontracted Purchase Order for the subcontracted Work Order
	from inventory_tools.inventory_tools.overrides.work_order import make_purchase_order

	subcontracted_wo = frappe.db.get_value(
		"Work Order",
		{
			"production_plan": pp.name,
			"supplier": "Credible Contract Baking",
			"docstatus": 1,
		},
		"name",
	)
	assert (
		subcontracted_wo
	), "Subcontracted Work Order for Pie Crust not found after production plan setup"
	po_name = make_purchase_order(subcontracted_wo, "Credible Contract Baking")
	assert po_name, "make_purchase_order did not return a PO name"
	po = frappe.get_doc("Purchase Order", po_name)
	po.submit()


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


def create_specifications(settings=None):
	for c in (
		("Red", "#E24C4C"),
		("Blue", "#2490EF"),
		("Purple", "#8684FF"),
		("Green", "#8CCF54"),
		("Yellow", "#FFFF00"),
		("White", "#EEEEEE"),
		("Black", "#111111"),
	):
		if not frappe.db.exists("Color", c[0]):
			color = frappe.new_doc("Color")
			color.name = c[0]
			color.color = c[1]
			color.save()

	for spec in SPECIFICATIONS:
		if frappe.db.exists("Specification", spec.get("name")):
			s = frappe.get_doc("Specification", spec.get("name"))
		else:
			s = frappe.new_doc("Specification")
			s.name = spec.get("name")
			s.dt = spec.get("dt")
			s.apply_on = spec.get("apply_on")
			s.enabled = spec.get("enabled")
			for at in spec.get("attributes"):
				s.append("attributes", at)
			s.save()


def create_demo_specification_values():
	"""
	run this if you need to manually create data for demoing faceted search
	bench execute 'inventory_tools.tests.setup.create_demo_specification_values'
	"""
	from inventory_tools.tests.test_faceted_search import (
		test_values_updated_on_item_save,
		test_generate_values,
		test_generate_values_on_overlapping_items,
		test_manual_attribute_addition,
	)

	test_values_updated_on_item_save()
	test_generate_values()
	test_generate_values_on_overlapping_items()
	test_manual_attribute_addition()


def create_item_dimensions():
	for item in ITEM_DIMENSIONS:
		pyd = frappe.new_doc("Physical Dimension")
		pyd.update(item)
		if pyd.reference_doctype == "Item":
			stock_uom = frappe.db.get_value("Item", pyd.reference_document, "stock_uom")
			pyd.item_uom = pyd.item_uom or stock_uom or pyd.uom
		pyd.save()


def create_warehouse_dimensions():
	for item in WAREHOUSE_DIMENSIONS:
		wyd = frappe.new_doc("Physical Dimension")
		wyd.update(item)
		wyd.save()


def _get_item_buying_rate(item_code):
	"""Get item rate from Bakery Buying price list."""
	return (
		frappe.db.get_value(
			"Item Price",
			{"item_code": item_code, "price_list": "Bakery Buying", "buying": 1},
			"price_list_rate",
		)
		or 0
	)


def create_stock_entries():
	j = len(ITEMS_STOCKENTRY) // 2
	# Add items to warehouse
	se = frappe.new_doc("Stock Entry")
	se.company = "Chelsea Fruit Co"
	se.posting_date = getdate().replace(month=1, day=1)
	se.set_posting_time = 1
	se.stock_entry_type = "Material Receipt"

	for item in ITEMS_STOCKENTRY[0:j]:
		se.append(
			"items",
			{
				"t_warehouse": item["warehouse"],
				"item_code": item["item_code"],
				"qty": item["qty"],
				"basic_rate": _get_item_buying_rate(item["item_code"]),
			},
		)

	se.save()
	se.submit()

	# Second entry offset time for FIFO/LIFO
	se = frappe.new_doc("Stock Entry")
	se.company = "Chelsea Fruit Co"
	se.posting_date = getdate().replace(month=1, day=2)
	se.set_posting_time = 1
	se.stock_entry_type = "Material Receipt"

	for item in ITEMS_STOCKENTRY[j:]:
		se.append(
			"items",
			{
				"t_warehouse": item["warehouse"],
				"item_code": item["item_code"],
				"qty": item["qty"],
				"basic_rate": _get_item_buying_rate(item["item_code"]),
			},
		)

	se.save()
	se.submit()

	# Raw materials in Storeroom - APC for production and Material Transfer for Manufacture test
	se = frappe.new_doc("Stock Entry")
	se.company = "Ambrosia Pie Company"
	se.posting_date = getdate().replace(month=1, day=1)
	se.set_posting_time = 1
	se.stock_entry_type = "Material Receipt"
	for item_code, qty in [("Flour", 100), ("Cornstarch", 50), ("Sugar", 50), ("Butter", 50)]:
		se.append(
			"items",
			{
				"item_code": item_code,
				"t_warehouse": "Storeroom - APC",
				"qty": qty,
				"basic_rate": _get_item_buying_rate(item_code),
			},
		)
	se.save()
	se.submit()
