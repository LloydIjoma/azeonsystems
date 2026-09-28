import frappe
import json

@frappe.whitelist(allow_guest=True)
def contact_sales():
    data = frappe.local.form_dict
    
    if not data and frappe.request.data:
        try:
            data = json.loads(frappe.request.data)
        except Exception:
            data = {}

    full_name = data.get("full_name")
    email = data.get("email")
    company_name = data.get("company_name")
    
    if not all([full_name, email, company_name]):
        frappe.local.response["http_status_code"] = 400
        return {"error": "Missing required fields (full_name, email, company_name)"}

    try:
        # Use ToDo or a standard communication log to prevent missing module errors
        todo = frappe.new_doc("ToDo")
        todo.description = f"Enterprise Custom Plan Inquiry\nCompany: {company_name}\nContact: {full_name} ({email})\nMessage: {data.get('message', 'None')}"
        todo.status = "Open"
        todo.priority = "High"
        todo.allocated_to = "Administrator"
        todo.insert(ignore_permissions=True)

        frappe.db.commit()

        return {
            "status": "success", 
            "message": "Enterprise inquiry registered successfully. Our sales team will contact you shortly."
        }

    except Exception as e:
        frappe.local.response["http_status_code"] = 500
        return {"status": "error", "message": str(e)}
