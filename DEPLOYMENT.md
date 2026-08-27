# Azeon Systems — Production Launch Checklist

Step-by-step path from a clean Ubuntu 22.04 VPS to a live, wildcard-SSL,
multi-tenant deployment. Follow in order — later steps assume earlier ones
are done. Where an earlier phase left an open gap, it's called out here
with the exact fix, not just a pointer back to that phase.

## 1. Provision the VPS

```bash
git clone <your-azeon-systems-repo> /opt/azeon-systems   # or scp the tree over
cd /opt/azeon-systems
sudo AZEON_CORE_SOURCE=<git-remote-or-local-path-to-azeon_core> ./scripts/vps_setup.sh
```

This installs Python 3.10, Node 18, MariaDB, Redis, Nginx, Certbot, initializes
the bench, and fetches `erpnext` + `azeon_core` into it. **`AZEON_CORE_SOURCE`
is required** — without it the script skips fetching `azeon_core` and every
future `bench --site <site> install-app azeon_core` call from the provisioner
will fail (branding/CEO-dashboard step only; the tenant site itself still
works).

## 2. Fix MariaDB root auth (flagged in Phase 2, unresolved until now)

Fresh MariaDB on Ubuntu 22.04 defaults to `unix_socket` auth for the OS
`root` user, but `bench new-site` needs a real password credential to
create each tenant's database:

```bash
sudo mysql -u root <<'SQL'
ALTER USER 'root'@'localhost' IDENTIFIED BY 'REPLACE_WITH_A_STRONG_PASSWORD';
FLUSH PRIVILEGES;
SQL
```

Record that password — it goes into `provisioner/.env` as
`MARIADB_ROOT_PASSWORD` in step 4.

## 3. Set VPS environment variables

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin provisioner
sudo mkdir -p /opt/azeon-systems/provisioner
sudo cp provisioner/app.py provisioner/requirements.txt /opt/azeon-systems/provisioner/
sudo cp provisioner/.env.example /opt/azeon-systems/provisioner/.env
sudo nano /opt/azeon-systems/provisioner/.env   # fill in real values:
```

| Variable                      | Value |
|--------------------------------|-------|
| `PROVISIONER_WEBHOOK_SECRET`   | `openssl rand -hex 32` — also goes in frontend's `.env.local` |
| `BENCH_DIR`                    | `/home/frappe/frappe-bench` |
| `FRAPPE_USER`                  | `frappe` |
| `DOMAIN_SUFFIX`                | `azeonsystems.com.ng` |
| `MARIADB_ROOT_PASSWORD`        | the password set in step 2 |

## 4. Grant the provisioner's sudo rule (flagged in Phase 2)

Systemd services have no TTY, so `sudo` inside `provisioner/app.py` needs a
`NOPASSWD` rule — scoped tightly, not blanket:

```
# /etc/sudoers.d/azeon-provisioner
provisioner ALL=(frappe) NOPASSWD: /home/frappe/frappe-bench/env/bin/python -m bench *, \
                                    /usr/local/bin/bench *
provisioner ALL=(root)   NOPASSWD: /usr/bin/systemctl reload nginx
```

Adjust the `bench` path to match `sudo -u frappe which bench`. Verify with
`sudo -l -U provisioner`.

## 5. Launch the Flask provisioner via systemd

```bash
cd /opt/azeon-systems/provisioner
sudo python3.10 -m venv venv
sudo ./venv/bin/pip install -r requirements.txt
sudo chown -R provisioner:provisioner /opt/azeon-systems/provisioner

sudo cp /opt/azeon-systems/../provisioner/azeon-provisioner.service /etc/systemd/system/ 2>/dev/null \
  || sudo cp provisioner/azeon-provisioner.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now azeon-provisioner
sudo systemctl status azeon-provisioner --no-pager
curl -s http://127.0.0.1:8001/healthz
```

## 6. Deploy the Next.js frontend

```bash
cd /opt/azeon-systems/frontend
cp .env.example .env.local   # fill in PROVISIONER_URL + PROVISIONER_WEBHOOK_SECRET
npm ci
npm run build
```

Run it under systemd (not `npm run dev`) so it survives reboots/crashes:

```ini
# /etc/systemd/system/azeon-frontend.service
[Unit]
Description=Azeon Systems Next.js frontend
After=network.target azeon-provisioner.service

[Service]
Type=simple
User=frontend
WorkingDirectory=/opt/azeon-systems/frontend
EnvironmentFile=/opt/azeon-systems/frontend/.env.local
ExecStart=/usr/bin/npm run start -- -p 3000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin frontend
sudo chown -R frontend:frontend /opt/azeon-systems/frontend
sudo systemctl daemon-reload
sudo systemctl enable --now azeon-frontend
```

Add a `location /` block on the apex domain's nginx server (or a separate
server block for `azeonsystems.com.ng` / `www.azeonsystems.com.ng`, distinct from
the tenant-subdomain proxy in `scripts/nginx_master.conf`) that proxies to
`127.0.0.1:3000`. `scripts/nginx_master.conf` as written routes
`azeonsystems.com.ng` to the Frappe bench upstream — split that server block
if the marketing site and the bench need to live on the same apex domain.

**Reminder from Phase 4**: `/api/signup` holds its HTTP connection open for
as long as provisioning takes (minutes). That's fine under `npm run start`
on a persistent Node process, which this systemd unit gives you. If this
frontend is ever redeployed to a serverless platform instead, that route
needs to change to client-side polling first — it will silently fail on a
short function timeout otherwise.

## 7. Point wildcard DNS at the VPS

At your DNS provider, create:

```
A     azeonsystems.com.ng        -> <VPS IP>
A     *.azeonsystems.com.ng      -> <VPS IP>
```

Propagation can take a few minutes to a few hours depending on your
provider's TTL. Confirm before moving on:

```bash
dig +short testcompany.azeonsystems.com.ng
```

## 8. Issue the wildcard SSL certificate and install the nginx template

```bash
sudo EMAIL=you@azeonsystems.com.ng DOMAIN=azeonsystems.com.ng ./scripts/setup_ssl.sh
```

Manual DNS-01 mode (the default, no DNS provider credentials required)
pauses for you to create a TXT record — do that when prompted. Note that
**manual mode does not auto-renew**; switch to a `DNS_PLUGIN` (Cloudflare,
Route53, etc.) before launch if you want unattended renewal in production,
otherwise put a calendar reminder ~80 days out.

## 9. Run the end-to-end verification

```bash
export PROVISIONER_URL=http://127.0.0.1:8001
export PROVISIONER_WEBHOOK_SECRET=<same secret as provisioner/.env>
python3 scripts/e2e_test.py --cleanup-hint
```

This creates a real throwaway tenant, drives it through the full
provision → poll → HTTPS-reachability lifecycle, and prints the
`bench drop-site` command to remove it afterwards. Run it again with
`--via-frontend` (pointing `FRONTEND_URL` at the live frontend) to smoke-test
the actual `/api/signup` path a real signup would take.

## 10. Security checklist before opening this to real traffic

- [ ] `ufw allow 22,80,443/tcp` then `ufw enable` — nothing else should be
      reachable from the internet (MariaDB/Redis/provisioner/frontend all
      bind to `127.0.0.1` only; confirm with `ss -tlnp`).
- [ ] `PROVISIONER_WEBHOOK_SECRET` is a real random 32+ byte value, not the
      placeholder from `.env.example`, and matches on both the provisioner
      and the frontend.
- [ ] The sudoers rule from step 4 is scoped to specific commands, not
      `NOPASSWD: ALL`.
- [ ] MariaDB root password (step 2) is set and stored securely — it grants
      full DB access across every tenant.
- [ ] `bench --site all set-config developer_mode 0` — developer mode must
      stay off in production.
- [ ] A scheduled `bench --site all backup --with-files` (cron or systemd
      timer) is in place before any real tenant data lands here.
- [ ] Certificate renewal is unattended (see step 8) or a human is
      reminded before it lapses.
- [ ] `scripts/e2e_test.py` passes against the real domain, not just
      localhost.
- [ ] `./env/bin/pip install requests boto3` has been run inside the
      bench's own virtualenv — azeon_core imports both directly
      (Paystack checkout + S3 backups) and neither ships with a stock
      bench install (see `azeon_core/README.md`).
- [ ] `paystack_secret_key` is set in each tenant's `site_config.json`
      (or via `bench --site <site> set-config`) before enabling paid
      checkout, and the webhook URL
      (`/api/method/azeon_core.payments.paystack.paystack_webhook`) is
      registered in the Paystack dashboard. Without the key,
      `initialize_transaction` fails closed rather than silently
      succeeding unauthenticated.
