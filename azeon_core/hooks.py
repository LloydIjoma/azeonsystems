from . import __version__ as app_version  # noqa: F401

app_name = "azeon_core"
app_title = "Azeon Systems Core"
app_publisher = "Azeon Systems"
app_description = (
    "Azeon Systems branding, CEO dashboard, subscription gating, and "
    "workspace defaults provisioned onto every SME tenant site."
)
app_email = "dev@azeonsystems.com.ng"
app_license = "MIT"

# --------------------------------------------------------------------------
# Branding — injected into every desk/website page load. CSS/JS built by
# `bench build` from this app's public/** (see azeon_core/public/). The
# logo is an inline SVG data URI so branding never depends on that build
# step having run/succeeded.
# --------------------------------------------------------------------------
app_include_css = "/assets/azeon_core/css/azeon_theme.css"
app_include_js = [
    "/assets/azeon_core/js/azeon_onboarding.js",
    # Shared KPI-card/progress-bar/table renderers used by every
    # departmental dashboard Page (see azeon_core/page/*/*.js). Loaded
    # globally so it's already defined by the time any of those pages'
    # own on_page_load scripts run.
    "/assets/azeon_core/js/azeon_dashboard_widgets.js",
    # NOTE: platform_admin.js is intentionally NOT included here. It is the
    # controller for a single Page (module path
    # azeon_core/azeon_core/page/platform_admin/platform_admin.js) and is
    # loaded by Frappe on-demand only when that page is opened. Including it
    # globally on every desk page load — as a stale copy under public/js/
    # previously was — throws `Cannot set properties of undefined (setting
    # 'on_page_load')` on every OTHER desk page, because
    # frappe.pages['platform-admin'] doesn't exist until that page is
    # actually opened.
    #
    # azeon_desk.js IS safe to load globally: it only ever touches
    # frappe.app.redirect_to_login, and only when
    # frappe.boot.platform_admin_enabled is true (main platform site only —
    # see boot_session below). On every tenant site it's a no-op.
    "/assets/azeon_core/js/azeon_desk.js",
]
website_include_js = ["/assets/azeon_core/js/branding_override.js"]

# --------------------------------------------------------------------------
# Frappe's own /app shell hardcodes Guest -> /login for every /app/* route
# (frappe/www/app.py). Platform Admin needs its own branded entry point
# instead, so this hook intercepts exactly one route (app/platform-admin)
# before Frappe's default resolver ever runs, and sends a logged-out visitor
# to /admin-login. Every other path — including every other /app/* desk
# page, on this site and on every tenant site azeon_core is installed on —
# falls through to azeon_core.platform_admin.resolve_platform_admin_path's
# call to Frappe's default resolve_path, so nothing else changes.
# --------------------------------------------------------------------------
website_path_resolver = "azeon_core.platform_admin.resolve_platform_admin_path"

# Exposes frappe.boot.platform_admin_enabled to the desk's client-side boot
# info — see azeon_core.platform_admin.add_platform_admin_boot_info and
# public/js/azeon_desk.js, which uses it to scope the branded desk-logout
# redirect to the main platform site only.
boot_session = "azeon_core.platform_admin.add_platform_admin_boot_info"

doctype_js = {
    "Customer": "public/js/doctype_scripts/customer.js",
}

app_logo_url = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 220' width='100%25' height='100%25'><g><path d='M 120 120 L 160 30 L 200 120 L 175 120 L 160 85 L 145 120 Z' fill='%23F26522'/><path d='M 100 120 L 150 20 L 165 20 L 115 120 Z' fill='%23F58220'/><line x1='115' y1='110' x2='145' y2='70' stroke='%23FFFFFF' stroke-width='4'/><line x1='145' y1='70' x2='175' y2='40' stroke='%23FFFFFF' stroke-width='4'/><line x1='115' y1='110' x2='175' y2='40' stroke='%23FFFFFF' stroke-width='3'/><circle cx='115' cy='110' r='7' fill='%23FFFFFF' stroke='%23F58220' stroke-width='3'/><circle cx='145' cy='70' r='7' fill='%23FFFFFF' stroke='%23F58220' stroke-width='3'/><circle cx='175' cy='40' r='7' fill='%23FFFFFF' stroke='%23F58220' stroke-width='3'/><path d='M 140 95 L 165 115 L 225 35 L 245 40 L 170 135 L 130 100 Z' fill='%230D5C9D'/><path d='M 225 35 L 250 35 L 245 60 Z' fill='%230D5C9D'/><path d='M 200 95 L 220 125 L 210 125 L 210 105 Z' fill='%230D5C9D'/></g><text x='20' y='170' font-family='sans-serif' font-weight='bold' font-size='42' fill='%230D5C9D'>Azeon <tspan font-weight='normal' fill='%230D5C9D'>Systems</tspan></text><text x='25' y='198' font-family='sans-serif' font-style='italic' font-size='16' fill='%23333333'>Your Business, Seamlessly Connected</text></svg>"
website_context = {
    "favicon": "/assets/azeon_core/images/azeon_logo.png",
    "splash_image": "/assets/azeon_core/images/azeon_logo.png",
}

# --------------------------------------------------------------------------
# Runs exactly once, immediately after
# `bench --site <site> install-app azeon_core` (see provisioner/app.py).
# setup_dashboard.after_install() runs the CEO dashboard build AND tenant
# role/notification/subscription-plan setup as a series of independently
# isolated stages — see that function's docstring.
# --------------------------------------------------------------------------
after_install = "azeon_core.setup_dashboard.after_install"

# --------------------------------------------------------------------------
# doc_events / scheduler_events must each be defined ONCE per app. Frappe
# reads these as plain module attributes, so a second `doc_events = {...}`
# (or `scheduler_events = {...}`) assignment would silently REPLACE this
# one rather than merge with it — keep every hook in the single dict below.
# --------------------------------------------------------------------------
doc_events = {
    "User": {
        "on_update": "azeon_core.audit_logger.log_sensitive_action",
        "on_trash": "azeon_core.audit_logger.log_sensitive_action",
    },
    "Subscription": {
        "on_update": [
            "azeon_core.subscription_gate.on_subscription_update",
            "azeon_core.audit_logger.log_sensitive_action",
        ]
    },
    "Sales Invoice": {
        "validate": "azeon_core.validations.sales_invoice.validate_invoice",
    },
}

scheduler_events = {
    "daily": [
        "azeon_core.subscription_gate.check_subscription_expirations",
        "azeon_core.telemetry.collect_site_metrics",
        "azeon_core.backup_manager.run_tenant_s3_backup",
    ]
}
