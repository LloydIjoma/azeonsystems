# azeon_core

Frappe app that provisions every Azeon Systems tenant with:

- Navy Blue (`#0D47A1`) / Orange (`#F57C00`) desk branding and
  Montserrat/Open Sans typography (`azeon_core/public/css/azeon_theme.css`)
- A default **CEO Dashboard** workspace (System Manager role only) with
  Number Cards for Daily Sales Revenue, Active Leads, Sales Pipeline Value,
  Warehouse Inventory Value, Low Stock Items, and Unpaid Invoices, plus a
  Sales Revenue Trend chart (`azeon_core/setup_dashboard.py`)

All of it runs once via the `after_install` hook — see `hooks.py`.

Per-tenant setup (assigning the signup's own admin user the tenant-admin
role, setting Company name, attaching an initial trialling Subscription
for whichever plan they picked) is a separate step the provisioner runs
right after `install-app` — see `azeon_core/utils/provision.py` and
`provisioner/app.py`.

## Payments

`azeon_core/payments/paystack.py` is the subscription checkout/webhook
integration (Nigerian market: cards, bank transfer, USSD via Paystack).
Set `paystack_secret_key` in each tenant's `site_config.json` and register
`https://{tenant}.azeonsystems.com.ng/api/method/azeon_core.payments.paystack.paystack_webhook`
in the Paystack dashboard before enabling it for real traffic — see that
file's module docstring for the full flow.

## Extra dependencies

`requests` and `boto3` aren't part of a stock bench environment and must
be installed into the bench's own virtualenv (not this repo's):

```bash
./env/bin/pip install requests boto3
```

`boto3` is only needed if `backup_manager.py`'s S3 upload path
(`s3_backup_bucket` + AWS credentials in site_config.json) is actually
used — the daily backup scheduler hook degrades to `local_only` without it
configured, but will still raise `ModuleNotFoundError` if boto3 itself
isn't installed at all.

## Getting this app onto the bench

`install-app` only activates an app that's already fetched into the bench's
`apps/` directory — it doesn't fetch source. Before the provisioner's
`bench --site <site> install-app azeon_core` will succeed for **any**
tenant, this app must be pulled into the bench **once**:

```bash
# from a git remote (recommended for production)
bench get-app azeon_core https://github.com/<your-org>/azeon_core.git

# or from a local path (e.g. during development)
bench get-app azeon_core /path/to/azeon-systems/azeon_core
```

`scripts/vps_setup.sh` now does this automatically if `AZEON_CORE_SOURCE`
is set when it runs; otherwise it prints a reminder and skips it, so the
VPS bootstrap doesn't hard-fail before this app has a real repo to fetch.

## Local development

```bash
bench get-app azeon_core /path/to/azeon-systems/azeon_core
bench --site <your-site> install-app azeon_core
bench build --app azeon_core
```
