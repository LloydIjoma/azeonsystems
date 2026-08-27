import frappe

def log_sensitive_action(doc, method):
    """
    Hook to capture critical configuration modifications across core DocTypes.
    """
    sensitive_doctypes = ["User", "Role Profile", "Tenant Branding", "Subscription"]
    
    if doc.doctype in sensitive_doctypes:
        user = frappe.session.user if frappe.session and frappe.session.user else "System"
        ip = getattr(frappe.local, "request_ip", "Internal")
        
        frappe.get_doc({
            "doctype": "Activity Log",
            "subject": f"Security Alert: {doc.doctype} '{doc.name}' modified ({method}) by {user}",
            "user": user,
            "ip_address": ip,
            "status": "Success"
        }).insert(ignore_permissions=True)
