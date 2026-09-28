import re
import subprocess

import frappe

# Must be a plausible DNS label sequence — this is the only thing standing
# between `domain_name` and a shell command below, so keep it strict.
_DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$")


@frappe.whitelist()
def provision_ssl(domain_name):
    """
    Runs Certbot non-interactively to generate and bind SSL certificates for
    a tenant domain.
    """
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw("Only a System Manager can provision SSL certificates.", frappe.PermissionError)

    domain_name = (domain_name or "").strip().lower()
    if not _DOMAIN_RE.match(domain_name):
        frappe.throw(f"'{domain_name}' is not a valid domain name.")

    if not frappe.db.exists("Tenant Domain", {"domain": domain_name, "status": "Active"}):
        return {"status": "failed", "reason": "Domain must be active before requesting SSL"}

    try:
        # List-form + shell=False: domain_name is validated above and never
        # passed through a shell, so there's no injection surface even
        # though it's caller-supplied. The previous version built this as
        # an interpolated shell=True string, which let a crafted
        # `domain_name` (e.g. containing `;` or `$(...)`) run arbitrary
        # commands as whatever user this process runs as.
        certbot_cmd = [
            "sudo", "certbot", "--nginx",
            "-d", domain_name,
            "--non-interactive", "--agree-tos", "--redirect",
            "-m", f"admin@{domain_name}",
        ]
        res = subprocess.run(certbot_cmd, check=True, capture_output=True, text=True)

        # Update record status
        frappe.db.set_value("Tenant Domain", {"domain": domain_name}, "ssl_active", 1)
        frappe.db.commit()

        return {"status": "success", "message": f"SSL successfully provisioned for {domain_name}"}

    except subprocess.CalledProcessError as e:
        frappe.log_error(f"Certbot Execution Failed: {e.stderr}", "SSL Provisioning Error")
        return {"status": "failed", "reason": e.stderr}
