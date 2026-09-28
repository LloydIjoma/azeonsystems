import frappe

# --------------------------------------------------------------------------
# DEPRECATED / DISABLED — DO NOT RE-ENABLE without a full security review.
#
# This endpoint used to provision a brand-new Frappe site directly from a
# `@frappe.whitelist(allow_guest=True)` method — i.e. reachable, unauthenticated,
# by anyone on the internet who could reach ANY tenant site (azeon_core is
# installed on every tenant, so the URL was predictable:
# https://<any-tenant>.azeonsystems.com.ng/api/method/azeon_core.provisioning_api.create_tenant_workspace).
#
# It also:
#   - ran `shutil.rmtree(site_path)` + `bench new-site --force` on whatever
#     slug the caller supplied, so a repeat anonymous request for an
#     EXISTING tenant's company_name would silently delete that tenant's
#     entire site before recreating an empty one (unauthenticated data
#     destruction);
#   - shelled out with hardcoded MariaDB root credentials
#     (`--mariadb-root-username root --mariadb-root-password root`);
#   - fell back to a hardcoded VPS IP (`142.93.200.78.nip.io`) as the
#     provisioning domain.
#
# Tenant provisioning is handled exclusively by the hardened, HMAC-signed
# Flask provisioner (see provisioner/app.py + DEPLOYMENT.md) reached via the
# Next.js frontend's /api/signup route. That is the only supported signup
# path. This function is kept as an inert stub (rather than deleted outright)
# in case anything still references the whitelisted method name.
# --------------------------------------------------------------------------
@frappe.whitelist(allow_guest=False)
def create_tenant_workspace(*args, **kwargs):
    frappe.throw(
        "This provisioning endpoint has been disabled. New tenants are "
        "created exclusively through the Azeon Systems provisioner service.",
        frappe.PermissionError,
    )
