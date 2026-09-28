"""
Tenant-local operations for the Platform Admin feature (see platform_admin.py).

Everything in this module is invoked EXCLUSIVELY via `bench --site <tenant>
execute azeon_core.tenant_admin_ops.<fn>`, spawned as a subprocess from the
platform site (see platform_admin._run_bench_execute). Nothing here carries
`@frappe.whitelist` on purpose: these functions run with full site access
(direct password writes, no permission checks) and must never be reachable
over HTTP, from this tenant's own site or anyone else's. Shell/`bench`
access is already an OS-level trust boundary, so that's the only door these
functions are meant to be opened through.
"""

import os

import frappe
from frappe.utils import cint, today
from frappe.utils.password import update_password as set_password_hash
from frappe.utils.password_strength import test_password_strength


def get_tenant_admin_info():
    """Return this site's identity + admin contact for the platform admin table."""
    info = frappe.db.get_value("User", "Administrator", ["email", "creation"], as_dict=True)
    return {
        "site": frappe.local.site,
        "admin_email": info.email if info else None,
        "creation": str(info.creation) if info and info.creation else None,
    }


def set_admin_password(email):
    """
    Set a new password for the user identified by `email` on this site.

    The new password is deliberately NOT accepted as an argument here: it is
    read from the AZEON_RESET_PASSWORD environment variable that the caller
    (platform_admin.reset_tenant_password) sets only for this subprocess.
    Command-line arguments (which is how `--kwargs` would otherwise carry it)
    are visible to any local user via `ps`; environment variables of a
    process are only visible to that user, which is the same trust level
    already required to reach this function at all.
    """
    new_password = os.environ.get("AZEON_RESET_PASSWORD")
    if not new_password:
        frappe.throw("AZEON_RESET_PASSWORD was not provided to the subprocess")

    user = frappe.db.get_value("User", {"email": email}, "name")
    if not user:
        frappe.throw(f"No user with email '{email}' on site {frappe.local.site}")

    min_score = cint(frappe.db.get_single_value("System Settings", "minimum_password_score") or 2)
    strength = test_password_strength(new_password, user_inputs=[email])
    if strength.get("score", 0) < min_score:
        frappe.throw("Password is too weak. Choose a longer, less predictable password.")

    set_password_hash(user, new_password, logout_all_sessions=True)
    frappe.db.set_value("User", user, "last_password_reset_date", today())
    frappe.db.set_value("User", user, "reset_password_key", "")
    frappe.db.commit()

    return {"ok": True, "user": user}
