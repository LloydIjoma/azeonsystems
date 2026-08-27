import frappe

def execute():
    user_email = "tenantadmin@azeonsystems.com.ng"
    if not frappe.db.exists("User", user_email):
        user = frappe.new_doc("User")
        user.email = user_email
        user.first_name = "Tenant"
        user.last_name = "Admin"
        user.send_welcome_email = 0
        user.insert(ignore_permissions=True)
        
        # Assign Azeon Tenant Admin role
        user.add_roles("Azeon Tenant Admin")
        print(f"User {user_email} created with Azeon Tenant Admin role.")
    else:
        print(f"User {user_email} already exists.")

