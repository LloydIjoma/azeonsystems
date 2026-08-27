import frappe

# Department dashboards (see azeon_core/dashboards.py + azeon_core/page/)
# are gated by ERPNext's own standard roles (Sales Manager, Accounts
# Manager, HR Manager, Purchase Manager, Stock Manager, ...) wherever a
# department already has one — reusing those means Sales/Finance/HR/
# Procurement doctype permissions ERPNext already ships correctly-scoped
# don't need to be rebuilt from scratch. "Azeon Manager" fills the one gap
# ERPNext doesn't have out of the box: a cross-department viewer (e.g. an
# ops manager or the CEO's direct report) who needs the consolidated
# Manager Dashboard without holding any single department's head role.
TENANT_ROLES = ["Azeon Tenant Admin", "Azeon Manager", "Azeon Field User"]


def create_tenant_roles():
    """
    Creates custom application roles for multi-tenant isolation.
    """
    for role in TENANT_ROLES:
        if not frappe.db.exists("Role", role):
            doc = frappe.new_doc("Role")
            doc.role_name = role
            doc.desk_access = 1
            doc.insert(ignore_permissions=True)

    # Assign permissions to Azeon Tenant Admin for core DocTypes
    doctypes = ["Customer", "Sales Order", "Sales Invoice"]
    for dt in doctypes:
        if not frappe.db.exists("Custom DocPerm", {"parent": dt, "role": "Azeon Tenant Admin"}):
            perm = frappe.new_doc("Custom DocPerm")
            perm.parent = dt
            perm.parenttype = "DocType"
            perm.parentfield = "permissions"
            perm.role = "Azeon Tenant Admin"
            perm.read = 1
            perm.write = 1
            perm.create = 1
            perm.submit = 1
            perm.cancel = 1
            perm.insert(ignore_permissions=True)

    frappe.db.commit()
    return "Tenant roles configured successfully."


def grant_tenant_admin_rights(user):
    """
    Gives a user genuine local-admin capability over THIS tenant's site:
    manage internal users, roles, and configuration — independently of any
    other tenant, since each tenant is already its own isolated Frappe
    site/database (see provisioner/app.py; there is no cross-tenant data
    for this to leak into).

    "Azeon Tenant Admin" alone is not enough for that: Frappe hardcodes
    User-role assignment and System Settings access to the System Manager
    role regardless of any Custom DocPerm you grant elsewhere, so actually
    granting "manage my own users and settings" means granting System
    Manager. "Azeon Tenant Admin" is kept alongside it for
    branding/dashboard-visibility purposes (see the Page/Workspace `roles`
    lists throughout this app).
    """
    if not user or not frappe.db.exists("User", user):
        return
    create_tenant_roles()
    frappe.get_doc("User", user).add_roles("System Manager", "Azeon Tenant Admin")
