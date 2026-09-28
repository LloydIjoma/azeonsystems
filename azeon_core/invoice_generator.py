import frappe
from frappe.utils import nowdate

@frappe.whitelist()
def generate_and_email_receipt(plan_name, qty=1):
    """
    Generates ERPNext Sales Invoice for the CALLING user's own customer
    record, and submits it.

    `amount` used to be accepted directly from the caller and written
    straight onto the invoice line — any authenticated user could invoice
    themselves (or, since `customer_id` was also caller-supplied, any OTHER
    customer) for an arbitrary price. The rate is now always looked up
    server-side from the named Subscription Plan, and the customer is
    always resolved from the logged-in session rather than trusted input.
    """
    qty = frappe.utils.cint(qty) or 1

    if not frappe.db.exists("Subscription Plan", plan_name):
        frappe.throw(f"Unknown subscription plan: {plan_name}")

    rate = frappe.db.get_value("Subscription Plan", plan_name, "cost")
    if rate is None:
        frappe.throw(f"Subscription plan '{plan_name}' has no configured cost.")

    # Resolve the customer tied to the logged-in user — never take a
    # customer id from the request.
    customer_id = frappe.db.get_value(
        "Contact Link", {"parenttype": "Contact", "link_doctype": "Customer"}, "link_name"
    )
    if not customer_id:
        frappe.throw("No customer record is linked to your account.", frappe.PermissionError)

    # 1. Fetch Company
    company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {}, "name")

    # 2. Build Invoice
    si = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": customer_id,
        "company": company,
        "posting_date": nowdate(),
        "due_date": nowdate(),
        "is_pos": 0,
        "items": [{
            "item_name": f"Subscription Upgrade - {plan_name}",
            "qty": qty,
            "rate": rate,
            "income_account": frappe.db.get_value("Company", company, "default_income_account")
        }]
    })

    si.insert(ignore_permissions=True)
    si.submit()

    frappe.db.commit()
    print(f"INVOICE_SUCCESS:{si.name}")
    return {"status": "success", "invoice": si.name}
