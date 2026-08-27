import frappe

@frappe.whitelist(allow_guest=False)
def get_user_dashboard_data():
    """
    Returns aggregated metrics for the authenticated portal/mobile user.
    """
    user = frappe.session.user
    
    # Resolve customer linked to active logged-in user
    customer = frappe.db.get_value("Contact Link", {"parenttype": "Contact", "link_doctype": "Customer"}, "link_name")
    
    orders_count = 0
    invoices_count = 0
    
    if customer:
        orders_count = frappe.db.count("Sales Order", {"customer": customer, "docstatus": 1})
        invoices_count = frappe.db.count("Sales Invoice", {"customer": customer, "docstatus": 1, "status": "Unpaid"})
        
    return {
        "status": "success",
        "user": user,
        "customer": customer,
        "metrics": {
            "active_orders": orders_count,
            "unpaid_invoices": invoices_count
        }
    }
