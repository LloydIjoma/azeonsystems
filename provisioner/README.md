# Azeon Systems — Tenant Provisioner

Flask webhook service that turns a "new tenant" signup event into a live
ERPNext site at `https://{tenant_slug}.azeonsystems.com.ng`. See `app.py` for
the full flow.

Deploy and run this **on the Linux VPS** (or via WSL/SSH) — never invoke it,
or the `bench` commands it wraps, from native Windows PowerShell, per
`CLAUDE.md` guideline #1.

## Deployment

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin provisioner
sudo mkdir -p /opt/azeon-systems/provisioner
sudo cp app.py requirements.txt /opt/azeon-systems/provisioner/
sudo cp .env.example /opt/azeon-systems/provisioner/.env   # then edit .env
cd /opt/azeon-systems/provisioner
sudo python3.10 -m venv venv
sudo ./venv/bin/pip install -r requirements.txt
sudo chown -R provisioner:provisioner /opt/azeon-systems/provisioner

sudo cp azeon-provisioner.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now azeon-provisioner
```

## Required sudo rule

The `provisioner` service account needs to run bench commands as the
`frappe` user, and to reload nginx, **without a password prompt** (systemd
services have no TTY). Scope this as tightly as possible — do **not** grant
blanket `NOPASSWD: ALL`:

```
# /etc/sudoers.d/azeon-provisioner
provisioner ALL=(frappe) NOPASSWD: /home/frappe/frappe-bench/env/bin/python -m bench *, \
                                    /usr/local/bin/bench *
provisioner ALL=(root)   NOPASSWD: /usr/bin/systemctl reload nginx
```

Adjust the `bench` path to match `which bench` under the `frappe` user.
Validate with `sudo -l -U provisioner` after installing.

## Reverse proxy

Point an internal nginx `location` (e.g. `/webhooks/provision` on your main
site, or a dedicated `provisioner.azeonsystems.com.ng` vhost) at
`127.0.0.1:8001`, restricted to your webhook source (Cloudflare, your own
signup backend, etc.). The service itself only binds to loopback.

## Known operational caveat — MariaDB root auth

`scripts/vps_setup.sh` does not set an explicit MariaDB root password
(fresh MariaDB on Ubuntu 22.04 defaults to `unix_socket` auth for the OS
`root` user). `bench new-site` needs a working root credential to create
each tenant's database. Either:

- Set a real MariaDB root password post-install and put it in
  `MARIADB_ROOT_PASSWORD` in `.env`, or
- Switch the root auth plugin so the `frappe` OS user can authenticate.

Without one of these, `bench new-site` will fail at the database-creation
step and the job will show `status: failed`.

## API

**`POST /webhooks/provision`** — HMAC-signed (`X-Azeon-Signature: sha256=<hex>`
over the raw body, keyed by `PROVISIONER_WEBHOOK_SECRET`).

```json
{
  "company_name": "Acme Corp",
  "admin_email": "founder@acme.com",
  "admin_password": "optional — generated securely if omitted",
  "tenant_slug": "optional override, still sanitized",
  "plan": "starter | professional | enterprise (default: starter)"
}
```

`admin_email` becomes the real login for the site's Administrator account
(passed as `bench new-site --admin-email`) — it's not just a label. `plan`
selects which Subscription Plan the tenant's initial 7-day trial runs on;
see `azeon_core/utils/provision.py::bootstrap_tenant`, which the
provisioner runs via `bench execute` right after `install-app azeon_core`.

Returns `202` with `{ job_id, slug, site_name, status_url }`.

**`GET /webhooks/provision/<job_id>`** — poll job status. The generated
`admin_password` is included exactly once, on the first read after
`status: completed`, then redacted from memory.

**`GET /healthz`** — liveness probe.
