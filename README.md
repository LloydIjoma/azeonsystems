# azeon_core

Frappe app that provisions every Azeon Systems tenant with:

- Navy Blue (`#0D47A1`) / Orange (`#F57C00`) desk branding and
  Montserrat/Open Sans typography (`azeon_core/public/css/azeon_theme.css`)
- A default **CEO Dashboard** workspace (System Manager role only) with
  Number Cards for Daily Sales Revenue, Active Leads, Sales Pipeline Value,
  Warehouse Inventory Value, Low Stock Items, and Unpaid Invoices, plus a
  Sales Revenue Trend chart (`azeon_core/setup_dashboard.py`)

All of it runs once via the `after_install` hook — see `hooks.py`.

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
