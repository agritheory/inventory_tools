import frappe


@frappe.whitelist()
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
        .where(WorkOrder.status == 'Not Started')
    ).run()
    
    if len(work_orders):
        return production_item
    
    return ""