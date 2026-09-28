import frappe

def repair_desk():
    # 1. Restore Home Workspace flags
    if frappe.db.exists("Workspace", "Home"):
        doc = frappe.get_doc("Workspace", "Home")
        doc.is_hidden = 0
        doc.public = 1
        doc.save(ignore_permissions=True)
    
    # 2. Reset corrupted desk settings causing the 500 render error
    frappe.db.sql("DELETE FROM `tabSingles` WHERE doctype='Desk Properties'")
    frappe.clear_cache()
    return "Desk workspace repaired successfully."
