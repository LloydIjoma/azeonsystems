"""
Platform Admin — lets a System Manager on the main Azeon site list every
tenant site on this bench, and reset a tenant's admin password / suspend /
unsuspend / delete a tenant, without shell access to the VPS.

Cross-tenant access model
--------------------------
azeon_core is installed on every tenant site (see provisioner/app.py), so a
plain `@frappe.whitelist()` + role check would let a System Manager on ANY
tenant reach these endpoints from their own site and act on every OTHER
tenant — a full cross-tenant isolation break. `_require_platform_admin_access`
therefore also requires `platform_admin_enabled` to be set in the current
site's site_config.json, a flag that must only ever be set on the main site:

    bench --site azeonsystems.com.ng set-config platform_admin_enabled 1

Reading/writing another site's data
------------------------------------
Each tenant is a fully separate Frappe site (own database). The safe way to
touch another site's database from within a running request is NOT to call
frappe.init()/frappe.connect() for that site in-process — that resets
frappe.local (session, form_dict, response, ...) out from under the current
request/response. Instead this module shells out to `bench --site <tenant>
execute <fn>` (for python-level operations) or plain `bench --site <tenant>
<command>` (for CLI-level operations like maintenance mode / drop-site),
exactly like provisioner/app.py already does for bootstrap_tenant — a fully
isolated process per tenant, no shared state.
"""

import json
import os
import re
import shutil
import subprocess

import frappe
from frappe import _
from frappe.utils import get_bench_path, get_sites

BENCH_BIN = shutil.which("bench") or "bench"
SUBPROCESS_TIMEOUT = 30
CLI_SUBPROCESS_TIMEOUT = 120
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TRACEBACK_LINE_RE = re.compile(r"^\w+(\.\w+)*(Error|Exception):\s*(.*)$")


def _require_platform_admin_access():
    frappe.only_for("System Manager")
    if not frappe.conf.get("platform_admin_enabled"):
        frappe.throw(
            _("Platform Admin is not available on this site."),
            frappe.PermissionError,
        )


def add_platform_admin_boot_info(bootinfo):
    """
    `boot_session` hook (see hooks.py). Exposes whether THIS site is the
    platform site to the desk's client-side boot info, so
    public/js/branded_logout.js can decide — per site, not per page —
    whether logging out of the desk should land on /admin-login instead of
    Frappe's default /login. azeon_core is installed on every tenant site
    too, so this must come from site_config (set only on the main site),
    never be hardcoded true.
    """
    bootinfo.platform_admin_enabled = bool(frappe.conf.get("platform_admin_enabled"))


def resolve_platform_admin_path(path):
    """
    `website_path_resolver` hook (see hooks.py). Frappe's own /app shell
    (frappe/www/app.py) hardcodes Guest -> /login for every /app/* route —
    there's no hook to change that redirect target from inside it. This
    function runs earlier, in the website path-resolution step, and is the
    supported way to intercept one specific route ahead of that.

    Only Guest visitors to exactly app/platform-admin are redirected, and
    only on a site with platform_admin_enabled set (i.e. only the main
    platform site — never a tenant site, even though azeon_core is
    installed on every tenant too). Every other path, on every site, falls
    through to Frappe's own default resolver unchanged.
    """
    if (
        path == "app/platform-admin"
        and frappe.session.user == "Guest"
        and frappe.conf.get("platform_admin_enabled")
    ):
        frappe.local.flags.redirect_location = "/admin-login"
        raise frappe.Redirect

    from frappe.website.path_resolver import resolve_path

    return resolve_path(path)


def _tenant_sites():
    """Every site on this bench except the platform site making the call."""
    return sorted(s for s in get_sites(frappe.local.sites_path) if s != frappe.local.site)


def _require_known_tenant(site):
    """Throw unless `site` is a real tenant site (never the platform site itself)."""
    if site not in _tenant_sites():
        frappe.throw(_("Unknown tenant site: {0}").format(site))


def _run_bench_execute(site, method, kwargs=None, extra_env=None):
    """Run a whitelisted python function on `site` via `bench execute`."""
    cmd = [BENCH_BIN, "--site", site, "execute", method]
    if kwargs:
        cmd += ["--kwargs", json.dumps(kwargs)]

    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    try:
        return subprocess.run(
            cmd,
            cwd=get_bench_path(),
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        frappe.throw(_("Timed out contacting tenant site '{0}'.").format(site))


def _run_bench_cli(args, timeout=CLI_SUBPROCESS_TIMEOUT):
    """Run a plain `bench <args>` CLI command (set-maintenance-mode, drop-site, ...)."""
    cmd = [BENCH_BIN] + args
    try:
        return subprocess.run(
            cmd,
            cwd=get_bench_path(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        frappe.throw(_("Timed out running: {0}").format(" ".join(cmd)))


def _last_error_message(result):
    """Best-effort extraction of a human-readable message from a failed run."""
    lines = [line for line in result.stderr.strip().splitlines() if line.strip()]
    if not lines:
        return "Unknown error"
    last_line = lines[-1]
    match = _TRACEBACK_LINE_RE.match(last_line)
    return match.group(3) if match else last_line


def _log_activity(subject, content=""):
    """Write an Activity Log entry on the main site, same shape as reset_tenant_password."""
    frappe.get_doc({
        "doctype": "Activity Log",
        "subject": subject,
        "content": content,
        "user": frappe.session.user,
        "status": "Success",
    }).insert(ignore_permissions=True)
    frappe.db.commit()


@frappe.whitelist()
def verify_platform_admin_login():
    """
    Called by www/admin-login.html right after a successful session login to
    confirm the just-authenticated user is actually allowed into Platform
    Admin. Read-only (no mutation), so it's called via GET from the login
    page — that page has no desk boot loaded and therefore no CSRF token,
    and GET requests are exempt from Frappe's CSRF check.
    """
    _require_platform_admin_access()
    return {"ok": True, "user": frappe.session.user}


@frappe.whitelist()
def get_all_tenants():
    """Return list of all tenant sites with admin email, creation date and suspended status."""
    _require_platform_admin_access()

    tenants = []
    bench_path = get_bench_path()
    sites_path = os.path.join(bench_path, "sites")

    for site in _tenant_sites():
        admin_email = None
        creation = None
        is_suspended = False

        try:
            site_config_path = os.path.join(sites_path, site, "site_config.json")
            if os.path.exists(site_config_path):
                with open(site_config_path) as f:
                    conf = json.load(f)
                    is_suspended = bool(conf.get("maintenance_mode"))

            result = _run_bench_execute(
                site,
                "azeon_core.tenant_admin_ops.get_tenant_admin_info",
                kwargs={},
            )
            if result.returncode == 0 and result.stdout.strip():
                info = json.loads(result.stdout.strip().splitlines()[-1])
                admin_email = info.get("admin_email")
                creation = info.get("creation")
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Platform Admin: get_all_tenants failed for {site}")

        tenants.append({
            "site": site,
            "admin_email": admin_email or "—",
            "creation": creation or "—",
            "is_suspended": is_suspended,
        })

    # Sort by creation date (newest first) if available
    tenants.sort(key=lambda x: x.get("creation") or "", reverse=True)
    return tenants


@frappe.whitelist()
def reset_tenant_password(site, email, new_password):
    """Reset the password for `email` on tenant `site` and log the action."""
    _require_platform_admin_access()

    site = (site or "").strip()
    email = (email or "").strip()

    _require_known_tenant(site)
    if not email or not EMAIL_RE.match(email):
        frappe.throw(_("A valid email address is required."))
    if not new_password or len(new_password) < 8:
        frappe.throw(_("Password must be at least 8 characters long."))

    result = _run_bench_execute(
        site,
        "azeon_core.tenant_admin_ops.set_admin_password",
        kwargs={"email": email},
        extra_env={"AZEON_RESET_PASSWORD": new_password},
    )

    if result.returncode != 0:
        frappe.log_error(
            title="Platform Admin: reset_tenant_password",
            message=(
                f"Failed to reset password for '{email}' on '{site}' "
                f"(requested by {frappe.session.user}).\n\nstderr:\n{result.stderr[-2000:]}"
            ),
        )
        frappe.throw(_("Could not reset password: {0}").format(_last_error_message(result)))

    _log_activity(
        _("Platform Admin: password reset for {0} on tenant {1}").format(email, site),
    )

    return {"success": True}


@frappe.whitelist()
def suspend_tenant(site):
    """Put `site` into maintenance mode so visitors see the maintenance page."""
    _require_platform_admin_access()

    site = (site or "").strip()
    _require_known_tenant(site)

    result = _run_bench_cli(["--site", site, "set-maintenance-mode", "on"])
    if result.returncode != 0:
        frappe.log_error(
            title="Platform Admin: suspend_tenant",
            message=(
                f"Failed to suspend '{site}' (requested by {frappe.session.user}).\n\n"
                f"stderr:\n{result.stderr[-2000:]}"
            ),
        )
        frappe.throw(_("Could not suspend tenant: {0}").format(_last_error_message(result)))

    _log_activity(
        _("Platform Admin: suspended tenant {0}").format(site),
        _("Tenant put into maintenance mode."),
    )

    return {"ok": True, "message": _("{0} has been suspended").format(site)}


@frappe.whitelist()
def unsuspend_tenant(site):
    """Take `site` out of maintenance mode."""
    _require_platform_admin_access()

    site = (site or "").strip()
    _require_known_tenant(site)

    result = _run_bench_cli(["--site", site, "set-maintenance-mode", "off"])
    if result.returncode != 0:
        frappe.log_error(
            title="Platform Admin: unsuspend_tenant",
            message=(
                f"Failed to unsuspend '{site}' (requested by {frappe.session.user}).\n\n"
                f"stderr:\n{result.stderr[-2000:]}"
            ),
        )
        frappe.throw(_("Could not unsuspend tenant: {0}").format(_last_error_message(result)))

    _log_activity(
        _("Platform Admin: unsuspended tenant {0}").format(site),
        _("Tenant taken out of maintenance mode."),
    )

    return {"ok": True, "message": _("{0} has been unsuspended").format(site)}


@frappe.whitelist()
def delete_tenant(site, confirm_site_name=None):
    """
    Permanently delete `site` (bench drop-site --force, DB backed up to archive
    first). `confirm_site_name` must exactly equal `site` — the frontend
    already enforces this by making the operator type the site name, and this
    is enforced again here so the endpoint can never be misused from a script
    or a stale/forged request without that explicit confirmation.
    """
    _require_platform_admin_access()

    site = (site or "").strip()
    _require_known_tenant(site)

    if (confirm_site_name or "").strip() != site:
        frappe.throw(_("Site name confirmation does not match. Deletion cancelled."))

    result = _run_bench_cli(["drop-site", site, "--force"])
    if result.returncode != 0:
        frappe.log_error(
            title="Platform Admin: delete_tenant",
            message=(
                f"Failed to delete '{site}' (requested by {frappe.session.user}).\n\n"
                f"stderr:\n{result.stderr[-2000:]}"
            ),
        )
        frappe.throw(_("Could not delete tenant: {0}").format(_last_error_message(result)))

    _log_activity(
        _("Platform Admin: deleted tenant {0}").format(site),
        _("Tenant permanently deleted (database backed up and moved to archive)."),
    )

    return {"ok": True, "message": _("{0} has been deleted").format(site)}
