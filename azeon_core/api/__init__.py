import frappe
from frappe.utils.password import update_password

@frappe.whitelist(allow_guest=True)
def signup():
    try:
        data = frappe.request.get_json() or frappe.local.form_dict
        company_name = data.get("company_name")
        email = data.get("email")
        password = data.get("password")
        plan = data.get("plan")
        
        if not email or not password or not company_name:
            frappe.local.response["http_status_code"] = 400
            return {"status": "error", "message": "Missing required fields"}
            
        if frappe.db.exists("User", email):
            frappe.local.response["http_status_code"] = 400
            return {"status": "error", "message": "User already exists"}
            
        frappe.flags.ignore_password_policy = True
        
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": company_name,
            "enabled": 1,
            "send_welcome_email": 0,
            "user_type": "System User",
            "roles": [{"role": "System Manager"}]
        })
        user.insert(ignore_permissions=True)
        
        update_password(email, password)
        
        frappe.db.commit()
        return {"status": "success", "message": "User registered successfully"}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Signup Error")
        frappe.local.response["http_status_code"] = 500
        return {"status": "error", "message": str(e)}
    finally:
        frappe.flags.ignore_password_policy = False

@frappe.whitelist(allow_guest=True)
def login():
    data = frappe.request.get_json() or frappe.local.form_dict
    usr = data.get("usr")
    pwd = data.get("pwd")
    try:
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(user=usr, pwd=pwd)
        login_manager.post_login()
        frappe.db.commit()
        return {"status": "success", "message": "Logged in successfully", "full_name": frappe.get_value("User", usr, "full_name")}
    except Exception as e:
        frappe.local.response["http_status_code"] = 401
        return {"status": "error", "message": "Invalid credentials"}
