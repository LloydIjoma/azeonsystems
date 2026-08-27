#!/usr/bin/env python3
"""
Azeon Systems — End-to-End Deployment Verification
====================================================
Exercises the full tenant-provisioning lifecycle against a live deployment:

  1. POST a signed request to the Flask provisioner's `/webhooks/provision`
     webhook — the same call the Next.js `/api/signup` route makes on the
     frontend's behalf — and assert a `202 Accepted`.
  2. Poll `/webhooks/provision/<job_id>` until the job reports `completed`
     or `failed`, or a timeout elapses.
  3. HTTP GET the resulting tenant subdomain and assert it actually
     resolves and serves something (ideally the Frappe login page).

A note on scope: the original spec for this script describes hitting
`/api/signup` directly and getting a `202` + job endpoint to poll. That
protocol (202 + job_id + status_url) is what the *provisioner* speaks —
`/api/signup` on the frontend already does the signing and polling
internally and only ever returns a single final 200/error to its caller
(see frontend/src/app/api/signup/route.ts). So by default this script
talks to the provisioner directly, which is what actually implements the
"signed request -> 202 -> poll" flow. Pass --via-frontend to instead
smoke-test the full stack through /api/signup as an end user's browser
would hit it (single blocking call, no manual signing needed).

Stdlib-only (no `requests` dependency) so it runs on a bare VPS Python
install with nothing extra to pip install.

This creates a REAL tenant site via `bench new-site` on whatever backend
it's pointed at. Don't run it against production without a cleanup plan —
pass --cleanup-hint to get the `bench drop-site` command printed at the end.

Usage:
    python scripts/e2e_test.py
    python scripts/e2e_test.py --via-frontend
    python scripts/e2e_test.py --cleanup-hint

Required environment variables (direct-provisioner mode):
    PROVISIONER_URL              e.g. http://127.0.0.1:8001
    PROVISIONER_WEBHOOK_SECRET   must match provisioner/.env

Optional:
    FRONTEND_URL                 default http://localhost:3000  (--via-frontend mode)
    DOMAIN_SUFFIX                default azeonsystems.com.ng
    TEST_COMPANY_NAME            default "Azeon E2E TestCo <random suffix>"
    TEST_ADMIN_EMAIL             default e2e-test@azeonsystems.com.ng
    POLL_INTERVAL_SECONDS        default 5
    POLL_TIMEOUT_SECONDS         default 900   (15 min — matches the provisioner's own ceiling)
    HTTP_CHECK_TIMEOUT_SECONDS   default 15
"""

import argparse
import hashlib
import hmac
import json
import os
import random
import string
import sys
import time
import urllib.error
import urllib.request

DEFAULT_DOMAIN_SUFFIX = "azeonsystems.com.ng"


def env(name, default=None):
    val = os.environ.get(name)
    return val if val not in (None, "") else default


def random_suffix(n=6):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def http_request(method, url, headers=None, body=None, timeout=15):
    data = body.encode("utf-8") if isinstance(body, str) else body
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace"), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace"), dict(exc.headers)


def sign(secret, raw_body):
    digest = hmac.new(secret.encode("utf-8"), raw_body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def fail(message):
    print(f"\n[FAIL] {message}")
    sys.exit(1)


def step(label):
    print(f"\n== {label} ==")


def run_direct_provisioner_flow(provisioner_url, webhook_secret, company_name, admin_email,
                                 poll_interval, poll_timeout):
    step("1/3 POST signed request to provisioner /webhooks/provision")
    payload = {"company_name": company_name, "admin_email": admin_email, "plan": "starter"}
    raw_body = json.dumps(payload)
    signature = sign(webhook_secret, raw_body)

    status, body, _ = http_request(
        "POST",
        f"{provisioner_url}/webhooks/provision",
        headers={"Content-Type": "application/json", "X-Azeon-Signature": signature},
        body=raw_body,
    )
    if status != 202:
        fail(f"expected 202 Accepted, got {status}: {body}")

    accepted = json.loads(body)
    job_id = accepted["job_id"]
    status_url = accepted["status_url"]
    print(f"  accepted: job_id={job_id} site_name={accepted['site_name']}")

    step("2/3 Poll provisioner job status until completed")
    deadline = time.time() + poll_timeout
    job = None
    while time.time() < deadline:
        time.sleep(poll_interval)
        s, b, _ = http_request("GET", f"{provisioner_url}{status_url}")
        if s != 200:
            print(f"  ... poll returned {s}, retrying")
            continue
        job = json.loads(b)
        print(f"  status={job['status']}")
        if job["status"] in ("completed", "failed"):
            break
    else:
        fail(f"provisioning did not finish within {poll_timeout}s")

    if job is None or job["status"] != "completed":
        fail(f"job ended in status={job.get('status') if job else 'unknown'}: "
             f"{job.get('error') if job else 'no response'}")

    print(f"  completed: site_name={job['site_name']}")
    return job["site_name"]


def run_via_frontend_flow(frontend_url, company_name, admin_email):
    step("1/3 POST to Next.js /api/signup (frontend signs + polls internally)")
    payload = {"companyName": company_name, "adminEmail": admin_email, "plan": "starter"}
    status, body, _ = http_request(
        "POST",
        f"{frontend_url}/api/signup",
        headers={"Content-Type": "application/json"},
        body=json.dumps(payload),
        timeout=900,
    )
    if status != 200:
        fail(f"expected 200 from /api/signup, got {status}: {body}")

    result = json.loads(body)
    tenant_url = result["tenantUrl"]
    print(f"  tenant ready: {tenant_url}")
    print("  2/3 (skipped — /api/signup already polled to completion internally)")
    return tenant_url.split("://", 1)[-1]


def check_tenant_reachable(site_name, timeout):
    step("3/3 HTTP GET the tenant subdomain")
    url = f"https://{site_name}"
    try:
        status, body, _ = http_request("GET", url, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 — surface any connection/TLS error plainly
        fail(f"GET {url} raised {exc!r}")
        return  # unreachable, fail() exits, but keeps type checkers happy

    if status >= 500:
        fail(f"GET {url} returned {status}")

    marker_found = "frappe" in body.lower() or "/assets/frappe" in body
    print(f"  GET {url} -> {status} "
          f"({'Frappe markers found' if marker_found else 'no Frappe markers found — check manually'})")
    return status


def main():
    parser = argparse.ArgumentParser(description="Azeon Systems end-to-end deployment verification")
    parser.add_argument("--via-frontend", action="store_true",
                         help="Go through Next.js /api/signup instead of hitting the provisioner directly")
    parser.add_argument("--cleanup-hint", action="store_true",
                         help="Print the bench command to remove the test tenant site afterwards")
    args = parser.parse_args()

    domain_suffix = env("DOMAIN_SUFFIX", DEFAULT_DOMAIN_SUFFIX)
    company_name = env("TEST_COMPANY_NAME", f"Azeon E2E TestCo {random_suffix()}")
    admin_email = env("TEST_ADMIN_EMAIL", "e2e-test@azeonsystems.com.ng")
    poll_interval = float(env("POLL_INTERVAL_SECONDS", "5"))
    poll_timeout = float(env("POLL_TIMEOUT_SECONDS", "900"))
    http_check_timeout = float(env("HTTP_CHECK_TIMEOUT_SECONDS", "15"))

    print(f"Company name : {company_name}")
    print(f"Domain suffix: {domain_suffix}")

    if args.via_frontend:
        frontend_url = env("FRONTEND_URL", "http://localhost:3000")
        site_name = run_via_frontend_flow(frontend_url, company_name, admin_email)
    else:
        provisioner_url = env("PROVISIONER_URL")
        webhook_secret = env("PROVISIONER_WEBHOOK_SECRET")
        if not provisioner_url or not webhook_secret:
            fail("PROVISIONER_URL and PROVISIONER_WEBHOOK_SECRET must be set (see provisioner/.env.example)")
        site_name = run_direct_provisioner_flow(
            provisioner_url, webhook_secret, company_name, admin_email, poll_interval, poll_timeout
        )

    check_tenant_reachable(site_name, http_check_timeout)

    print("\n[PASS] End-to-end tenant provisioning verified.")
    if args.cleanup_hint:
        print(f"\nTo remove the test tenant afterwards, run on the VPS as the frappe user:\n"
              f"  bench drop-site {site_name} --force")


if __name__ == "__main__":
    main()
