"""
Per-tenant bootstrap — runs ONCE per new tenant, right after
`bench --site <site> install-app azeon_core` (see provisioner/app.py step
5). This is distinct from `setup_dashboard.after_install`, which runs
once per app install and builds the CEO dashboard / tenant roles /
Subscription Plan docs that exist identically on every site; this module
does the work that's specific to THIS tenant's signup (their company name,
their admin user, their chosen plan).

Previously this file exposed a `setup_new_tenant(site_name)` whitelisted
method that called `install_app("azeon_core", ...)` on whatever site
happened to be connected — but by the time any HTTP request could reach a
whitelisted method on a tenant site, azeon_core is already installed (the
provisioner installs it via `bench install-app` before the site ever
serves a request), so that function could never usefully run. Replaced
with the real per-signup bootstrap below.
"""

import frappe
from frappe.utils import add_days, nowdate

from azeon_core.setup_subscription_plans import create_plans
from azeon_core.subscription_gate import PLAN_KEY_MAP, apply_tenant_module_limits
from azeon_core.utils.roles import grant_tenant_admin_rights

TRIAL_DAYS = 7


@frappe.whitelist(allow_guest=False)
def bootstrap_tenant(company_name, admin_email, plan="starter"):
    """
    Assigns the tenant's real admin user their role, sets the Company name
    from signup, ensures Subscription Plan docs exist, and attaches an
    initial (trialling) Subscription for the chosen plan so module gating
    (subscription_gate.PLAN_MODULE_MAP) applies from minute one instead of
    leaving every module unlocked until the first payment webhook fires.

    Only reachable as Administrator: on a brand new site there is no other
    user yet, and `bench --site <site> execute` (how the provisioner calls
    this) always runs as Administrator. Left `@frappe.whitelist` only so
    it can also be smoke-tested by hand from the desk console.
    """
    if frappe.session.user != "Administrator":
        frappe.throw("Only Administrator can bootstrap a new tenant.", frappe.PermissionError)

    plan_name = PLAN_KEY_MAP.get((plan or "").lower(), "Azeon Starter")

    # 1. Local admin rights (Task: "every newly signed-up tenant
    #    automatically receives local administrator rights"). The
    #    tenant's admin_email becomes the EMAIL FIELD on the site's
    #    Administrator account (see provisioner/app.py's `--admin-email`)
    #    — the User record's `name` stays the literal string
    #    "Administrator", it is never renamed to the email address. An
    #    earlier version of this function checked
    #    `frappe.db.exists("User", admin_email)`, which is therefore
    #    always False and silently never granted anything. Grant the
    #    Administrator record directly instead.
    grant_tenant_admin_rights("Administrator")

    # 2. Company name, so ERPNext isn't left on its demo default.
    default_company = frappe.db.get_single_value("Global Defaults", "default_company")
    if company_name and default_company and frappe.db.exists("Company", default_company):
        frappe.db.set_value("Company", default_company, "company_name", company_name)

    # 3. Make sure every Subscription Plan this tenant could ever be on exists.
    create_plans()

    # 4. Attach an initial trialling Subscription for the chosen plan.
    customer = _ensure_billing_customer(company_name or admin_email)
    if not frappe.db.exists("Subscription", {"party": customer}):
        frappe.get_doc({
            "doctype": "Subscription",
            "party_type": "Customer",
            "party": customer,
            "status": "Trialling",
            "trial_period_start": nowdate(),
            "trial_period_end": add_days(nowdate(), TRIAL_DAYS),
            "plans": [{"plan": plan_name, "qty": 1}],
        }).insert(ignore_permissions=True)

    apply_tenant_module_limits(plan_name)
    frappe.db.commit()

    return {"status": "success", "plan": plan_name, "customer": customer}


def _ensure_billing_customer(customer_name):
    if not frappe.db.exists("Customer", customer_name):
        group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "All Customer Groups"
        frappe.get_doc({
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_group": group,
        }).insert(ignore_permissions=True)
    return customer_name
