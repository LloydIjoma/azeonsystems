import frappe

def seed_test_subscription():
    cg = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
    if not cg:
        cg = "Commercial"
        if not frappe.db.exists("Customer Group", cg):
            frappe.get_doc({"doctype": "Customer Group", "customer_group_name": cg, "is_group": 0}).insert(ignore_permissions=True)

    if not frappe.db.exists("Customer", "CUST-001"):
        frappe.get_doc({"doctype": "Customer", "customer_name": "CUST-001", "customer_group": cg}).insert(ignore_permissions=True)

    if not frappe.db.exists("Subscription Plan", "Azeon Starter"):
        frappe.get_doc({"doctype": "Subscription Plan", "plan_name": "Azeon Starter", "billing_interval": "Month", "cost": 50}).insert(ignore_permissions=True)

    if not frappe.db.exists("Subscription Plan", "Azeon Professional"):
        frappe.get_doc({"doctype": "Subscription Plan", "plan_name": "Azeon Professional", "billing_interval": "Month", "cost": 150}).insert(ignore_permissions=True)

    if not frappe.db.exists("Subscription", {"party": "CUST-001"}):
        sub = frappe.get_doc({
            "doctype": "Subscription",
            "party_type": "Customer",
            "party": "CUST-001",
            "status": "Active",
            "plans": [{"plan": "Azeon Starter", "qty": 1}]
        })
        sub.insert(ignore_permissions=True)

    frappe.db.commit()
    print("SEED_COMPLETE")
