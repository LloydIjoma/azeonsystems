"""
Azeon Systems - Tenant Provisioner
===================================
Flask webhook service that receives a "new tenant signed up" event and
provisions a dedicated Frappe/ERPNext site on this VPS's bench.

Runs on the Linux VPS under gunicorn + systemd (see azeon-provisioner.service).
Never invoke bench from Windows PowerShell — this service IS the thing that
runs bench, and it must run on Linux, per CLAUDE.md guideline #1.

Flow:
  1. POST /webhooks/provision  (HMAC-signed)
       -> validates payload, slugifies company_name (CLAUDE.md guideline #2),
          checks for slug collisions, spawns a background thread, returns
          202 immediately with a job_id.
  2. Background thread:
       -> bench new-site <slug>.azeonsystems.com.ng  (creates DB + admin user)
       -> bench --site <slug>.azeonsystems.com.ng install-app erpnext
       -> bench --site <slug>.azeonsystems.com.ng install-app azeon_core
            (Azeon branding + CEO Dashboard — see azeon_core/hooks.py;
             must already be fetched into the bench via `bench get-app`)
       -> bench --site <slug>.azeonsystems.com.ng execute
            azeon_core.utils.provision.bootstrap_tenant
            (assigns tenant-admin role, sets Company name, attaches an
             initial trialling Subscription for the chosen plan so module
             gating applies immediately — see that function's docstring)
       -> bench setup nginx --yes  +  systemctl reload nginx
  3. GET /webhooks/provision/<job_id>
       -> poll job status; the generated admin password is returned exactly
          once (on the first "completed" read) and then redacted from memory.
"""

import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request

PLAN_VALUES = {"starter", "professional", "enterprise"}

# --------------------------------------------------------------------------
# Configuration — override via environment (see .env.example / systemd
# EnvironmentFile). Fail loudly at import time if anything security-critical
# is missing, rather than silently running unauthenticated.
# --------------------------------------------------------------------------
BENCH_DIR = os.environ.get("BENCH_DIR", "/home/frappe/frappe-bench")
FRAPPE_USER = os.environ.get("FRAPPE_USER", "frappe")
DOMAIN_SUFFIX = os.environ.get("DOMAIN_SUFFIX", "azeonsystems.com.ng")
MARIADB_ROOT_PASSWORD = os.environ.get("MARIADB_ROOT_PASSWORD", "")
WEBHOOK_SECRET = os.environ.get("PROVISIONER_WEBHOOK_SECRET", "")
BENCH_BIN = os.environ.get("BENCH_BIN", "bench")
PROVISION_TIMEOUT_SECONDS = int(os.environ.get("PROVISION_TIMEOUT_SECONDS", "900"))

RESERVED_SLUGS = {
    "www", "api", "app", "admin", "provisioner", "mail", "ftp", "smtp",
    "assets", "static", "cdn", "root", "system", "erpnext", "frappe",
    "billing", "status", "support", "docs", "blog",
}

if not WEBHOOK_SECRET:
    raise RuntimeError(
        "PROVISIONER_WEBHOOK_SECRET is not set. Refusing to start an "
        "unauthenticated provisioning webhook."
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("azeon.provisioner")

app = Flask(__name__)

# In-memory job tracking. Fine for a single gunicorn worker at Azeon's
# current scale; move to Redis/RQ before running >1 worker process, since
# job state would otherwise be split across processes.
_JOBS_LOCK = threading.Lock()
JOBS = {}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def slugify(company_name: str) -> str:
    """
    Sanitize a company name into a lowercase alphanumeric DNS-safe slug,
    per CLAUDE.md guideline #2 ("Sanitize user inputs into lowercase,
    alphanumeric slugs for site names").
    """
    if not company_name or not isinstance(company_name, str):
        raise ValueError("company_name must be a non-empty string")

    slug = company_name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")

    # DNS labels max out at 63 chars; leave headroom.
    slug = slug[:50].strip("-")

    if not slug:
        raise ValueError("company_name did not produce a usable slug")

    if slug in RESERVED_SLUGS:
        raise ValueError(f"'{slug}' is a reserved slug")

    if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", slug):
        raise ValueError(f"'{slug}' is not a valid DNS label")

    return slug


def verify_signature(raw_body: bytes, signature_header: str) -> bool:
    """
    Verify an HMAC-SHA256 signature over the raw request body, expected as
    'sha256=<hex digest>' (GitHub-webhook style). Uses constant-time compare.
    """
    if not signature_header or "=" not in signature_header:
        return False

    algo, _, provided = signature_header.partition("=")
    if algo != "sha256":
        return False

    expected = hmac.new(WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided.strip())


def site_name_for(slug: str) -> str:
    return f"{slug}.{DOMAIN_SUFFIX}"


def site_exists(slug: str) -> bool:
    return (Path(BENCH_DIR) / "sites" / site_name_for(slug)).exists()


def run_as_frappe(args, timeout=PROVISION_TIMEOUT_SECONDS):
    """
    Run a command as the `frappe` bench-owning user, in the bench directory.
    Requires the provisioner's service account to have a narrowly-scoped
    NOPASSWD sudo rule for this (see provisioner/README.md).
    """
    cmd = ["sudo", "-u", FRAPPE_USER, "-H"] + args
    logger.info("Running: %s", " ".join(cmd[:-1] + [cmd[-1].split(" ")[0]]))
    return subprocess.run(
        cmd,
        cwd=BENCH_DIR,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _set_job(job_id, **fields):
    with _JOBS_LOCK:
        JOBS[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        JOBS[job_id].update(fields)


def _append_step(job_id, step, ok, detail=""):
    with _JOBS_LOCK:
        JOBS[job_id]["steps"].append(
            {"step": step, "ok": ok, "detail": detail[-4000:]}
        )


# --------------------------------------------------------------------------
# Provisioning pipeline (runs in a background thread)
# --------------------------------------------------------------------------
def provision_tenant(job_id, slug, company_name, admin_email, admin_password, plan):
    site_name = site_name_for(slug)
    try:
        _set_job(job_id, status="creating_site")

        new_site_cmd = [
            BENCH_BIN, "new-site", site_name,
            "--admin-password", admin_password,
            # Without this, every tenant's actual login is the default
            # "admin@example.com" regardless of what the customer entered
            # at signup — they'd never be able to log in with the email
            # they were told was their admin_email.
            "--admin-email", admin_email,
        ]
        if MARIADB_ROOT_PASSWORD:
            new_site_cmd += ["--db-root-password", MARIADB_ROOT_PASSWORD]
        new_site_cmd += ["--no-mariadb-socket"]

        result = run_as_frappe(new_site_cmd)
        _append_step(job_id, "bench new-site", result.returncode == 0, result.stdout + result.stderr)
        if result.returncode != 0:
            raise RuntimeError(f"bench new-site failed: {result.stderr[-2000:]}")

        _set_job(job_id, status="installing_erpnext")
        result = run_as_frappe([BENCH_BIN, "--site", site_name, "install-app", "erpnext"])
        _append_step(job_id, "bench install-app erpnext", result.returncode == 0, result.stdout + result.stderr)
        if result.returncode != 0:
            raise RuntimeError(f"install-app erpnext failed: {result.stderr[-2000:]}")

        _set_job(job_id, status="installing_azeon_core")
        result = run_as_frappe([BENCH_BIN, "--site", site_name, "install-app", "azeon_core"])
        _append_step(job_id, "bench install-app azeon_core", result.returncode == 0, result.stdout + result.stderr)
        if result.returncode != 0:
            # azeon_core only carries branding + the CEO dashboard — a
            # tenant with a working ERPNext site but no branding/dashboard
            # is still usable, so this failure is logged but does not
            # abort provisioning the way the erpnext step above does.
            logger.error("install-app azeon_core failed for %s: %s", site_name, result.stderr[-2000:])

        _set_job(job_id, status="bootstrapping_tenant")
        bootstrap_kwargs = json.dumps({
            "company_name": company_name,
            "admin_email": admin_email,
            "plan": plan,
        })
        result = run_as_frappe([
            BENCH_BIN, "--site", site_name, "execute",
            "azeon_core.utils.provision.bootstrap_tenant",
            "--kwargs", bootstrap_kwargs,
        ])
        _append_step(job_id, "bench execute bootstrap_tenant", result.returncode == 0, result.stdout + result.stderr)
        if result.returncode != 0:
            # Same tolerance as the azeon_core install step above: a tenant
            # that didn't get its initial role/Subscription bootstrapped is
            # still a usable ERPNext site, just ungated until fixed by hand.
            logger.error("bootstrap_tenant failed for %s: %s", site_name, result.stderr[-2000:])

        _set_job(job_id, status="setting_site_config")
        # Record the tenant's company name / admin email on the site itself
        # so the frontend can read it back via the Frappe REST API later.
        result = run_as_frappe([
            BENCH_BIN, "--site", site_name, "set-config",
            "azeon_company_name", company_name,
        ])
        _append_step(job_id, "bench set-config company_name", result.returncode == 0, result.stdout + result.stderr)

        _set_job(job_id, status="reloading_nginx")
        result = run_as_frappe([BENCH_BIN, "setup", "nginx", "--yes"])
        _append_step(job_id, "bench setup nginx", result.returncode == 0, result.stdout + result.stderr)

        reload_result = subprocess.run(
            ["sudo", "systemctl", "reload", "nginx"],
            capture_output=True, text=True, timeout=60, check=False,
        )
        _append_step(job_id, "systemctl reload nginx", reload_result.returncode == 0,
                     reload_result.stdout + reload_result.stderr)

        _set_job(
            job_id,
            status="completed",
            site_name=site_name,
            admin_email=admin_email,
            admin_password=admin_password,  # returned once via GET, then redacted
        )
        logger.info("Provisioning completed for %s", site_name)

    except Exception as exc:  # noqa: BLE001 — surface any failure to the job record
        logger.exception("Provisioning failed for %s", site_name)
        _set_job(job_id, status="failed", error=str(exc))


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    bench_ok = Path(BENCH_DIR).exists()
    return jsonify(status="ok" if bench_ok else "degraded", bench_dir_exists=bench_ok), (200 if bench_ok else 503)


@app.post("/webhooks/provision")
def provision_webhook():
    raw_body = request.get_data()
    signature = request.headers.get("X-Azeon-Signature", "")

    if not verify_signature(raw_body, signature):
        logger.warning("Rejected webhook with invalid/missing signature from %s", request.remote_addr)
        return jsonify(error="invalid signature"), 401

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="expected a JSON object body"), 400

    company_name = payload.get("company_name")
    admin_email = payload.get("admin_email")
    admin_password = payload.get("admin_password") or secrets.token_urlsafe(16)
    slug_override = payload.get("tenant_slug")
    plan = payload.get("plan") or "starter"

    if not admin_email or not EMAIL_RE.match(admin_email):
        return jsonify(error="admin_email is required and must be a valid email"), 400

    if plan not in PLAN_VALUES:
        return jsonify(error=f"plan must be one of: {', '.join(sorted(PLAN_VALUES))}"), 400

    try:
        slug = slugify(slug_override or company_name)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    if site_exists(slug):
        return jsonify(error=f"a site already exists for slug '{slug}'"), 409

    job_id = str(uuid.uuid4())
    with _JOBS_LOCK:
        JOBS[job_id] = {
            "job_id": job_id,
            "slug": slug,
            "site_name": site_name_for(slug),
            "status": "queued",
            "steps": [],
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    thread = threading.Thread(
        target=provision_tenant,
        args=(job_id, slug, company_name, admin_email, admin_password, plan),
        daemon=True,
    )
    thread.start()

    return jsonify(
        job_id=job_id,
        slug=slug,
        site_name=site_name_for(slug),
        status_url=f"/webhooks/provision/{job_id}",
    ), 202


@app.get("/webhooks/provision/<job_id>")
def provision_status(job_id):
    with _JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return jsonify(error="unknown job_id"), 404

        response = dict(job)
        # Reveal the generated admin password exactly once, then redact it
        # from the in-memory record.
        if job["status"] == "completed" and "admin_password" in job:
            job.pop("admin_password", None)

    return jsonify(response)


if __name__ == "__main__":
    # Development only. In production this app is served by gunicorn via
    # azeon-provisioner.service — see provisioner/README.md.
    app.run(host="127.0.0.1", port=8001, debug=False)
