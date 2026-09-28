import hashlib
import hmac
import time

import frappe
from frappe.model.naming import append_number_if_name_exists

PLAN_MODULE_MAP = {
    "Azeon 7-Day Trial": ["CRM", "Selling"],
    "Azeon Starter": ["CRM", "Selling", "Stock", "Buying"],
    "Azeon Professional": ["CRM", "Selling", "Stock", "Buying", "Accounts", "HR", "Projects"],
    "Azeon Enterprise": ["*"]
}

# Self-serve plan keys (as used by the frontend pricing page and signup
# form) mapped to the real Subscription Plan names. Shared by every payment
# integration (Stripe, Paystack, ...) so a webhook can never write an
# unrecognized string into a Subscription doc.
PLAN_KEY_MAP = {
    "starter": "Azeon Starter",
    "professional": "Azeon Professional",
    "enterprise": "Azeon Enterprise",
}


def apply_tenant_module_limits(subscription_plan_name):
    allowed_modules = PLAN_MODULE_MAP.get(subscription_plan_name, ["CRM", "Selling"])
    workspaces = frappe.get_all("Workspace", fields=["name", "module"])

    for ws in workspaces:
        if "*" in allowed_modules:
            frappe.db.set_value("Workspace", ws.name, "is_hidden", 0)
            continue

        if ws.module and ws.module not in allowed_modules:
            frappe.db.set_value("Workspace", ws.name, "is_hidden", 1)
        else:
            frappe.db.set_value("Workspace", ws.name, "is_hidden", 0)

    frappe.clear_cache()
    print(f"Successfully applied module gating for plan: {subscription_plan_name}")


def activate_subscription_for_party(party, plan_name):
    """
    Shared by every payment integration's webhook handler: given a party
    (Customer) already linked to a Subscription on THIS site, set that
    Subscription Active on the given plan and re-apply module gating.
    Returns the Subscription name, or None if no Subscription is linked to
    that party (callers should treat that as "ignore this event" rather
    than silently upgrading some other, unrelated subscription).
    """
    subscription_name = frappe.db.get_value("Subscription", {"party": party})
    if not subscription_name:
        return None

    doc = frappe.get_doc("Subscription", subscription_name)
    doc.status = "Active"
    if doc.plans:
        doc.plans[0].plan = plan_name
    doc.save(ignore_permissions=True)

    apply_tenant_module_limits(plan_name)
    frappe.db.commit()
    return subscription_name


def on_subscription_update(doc, method):
    if doc.status in ["Active", "Trialling"] and doc.plans:
        plan_name = doc.plans[0].plan
        apply_tenant_module_limits(plan_name)


def check_subscription_expirations():
    today = frappe.utils.today()
    expired_subscriptions = frappe.get_all(
        "Subscription",
        filters={
            "status": ["in", ["Active", "Trialling"]],
            "current_invoice_end": ["<", today]
        },
        fields=["name", "company"]
    )

    for sub in expired_subscriptions:
        doc = frappe.get_doc("Subscription", sub.name)
        doc.status = "Cancelled"
        doc.save(ignore_permissions=True)
        apply_tenant_module_limits("Expired")
        print(f"Subscription {sub.name} for {sub.company} has expired and was auto-cancelled.")

    frappe.db.commit()


def create_onboarded_field():
    """
    Standard Frappe "User" has no "onboarded" column — complete_onboarding()
    below needs somewhere to persist that a tenant admin has been through
    azeon_core's first-run onboarding wizard (public/js/azeon_onboarding.js),
    so add it as a Custom Field. Idempotent (create_custom_field no-ops if
    it already exists) — safe to call from both after_install (new
    tenants) and the add_user_onboarded_field patch (tenants provisioned
    before this field existed, backfilled via `bench migrate`).
    """
    from frappe.custom.doctype.custom_field.custom_field import create_custom_field

    create_custom_field(
        "User",
        {
            "fieldname": "onboarded",
            "label": "Onboarded",
            "fieldtype": "Check",
            "default": "0",
            "insert_after": "enabled",
            "description": (
                "Set once a tenant admin has completed azeon_core's "
                "first-run onboarding wizard."
            ),
        },
    )


@frappe.whitelist()
def complete_onboarding(data):
    import json
    if isinstance(data, str):
        data = json.loads(data)

    user = frappe.get_doc("User", frappe.session.user)
    user.db_set("onboarded", 1)

    if data.get("company_name"):
        new_company_name = data.get("company_name")
        company = frappe.db.get_value("Global Defaults", None, "default_company")
        if company and frappe.db.exists("Company", company):
            # Company.company_name is unique. A stray second Company
            # (e.g. an ERPNext-created "<name> (Demo)" default) can already
            # hold the name the wizard wants to rename the default company
            # to — set_value would then hit:
            #   pymysql.err.IntegrityError: (1062, "Duplicate entry '...'
            #   for key 'company_name'")
            # and 500 the whole onboarding call. Resolve it the same way
            # Frappe itself resolves duplicate names elsewhere (e.g. two
            # Users with the same full name) — via
            # frappe.model.naming.append_number_if_name_exists, which
            # appends "-1", "-2", ... until the value is unique. The
            # `filters` exclusion makes renaming a company to its OWN
            # current name a no-op instead of picking up a spurious "-1".
            unique_company_name = append_number_if_name_exists(
                "Company",
                new_company_name,
                fieldname="company_name",
                filters={"name": ["!=", company]},
            )
            frappe.db.set_value("Company", company, "company_name", unique_company_name)

    frappe.db.commit()
    return {"status": "success"}


# How much clock skew to tolerate between a webhook event's timestamp and
# now, to limit replay of a captured (but validly-signed) payload.
WEBHOOK_TOLERANCE_SECONDS = 300


def _verify_stripe_signature(raw_body: bytes, sig_header: str) -> bool:
    """
    Manually verify Stripe's 'Stripe-Signature' header, per Stripe's
    documented scheme, against `stripe_webhook_secret` in site_config.json.
    No `stripe` SDK dependency required — same manual-HMAC approach the
    provisioner already uses for its own webhook (see provisioner/app.py).
    """
    secret = frappe.conf.get("stripe_webhook_secret")
    if not secret:
        frappe.log_error("stripe_webhook_secret is not set in site_config.json", "Stripe Webhook")
        return False

    if not sig_header:
        return False

    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        return False

    try:
        if abs(time.time() - int(timestamp)) > WEBHOOK_TOLERANCE_SECONDS:
            return False
    except ValueError:
        return False

    signed_payload = f"{timestamp}.".encode() + raw_body
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@frappe.whitelist(allow_guest=True)
def stripe_webhook():
    """
    Guest-accessible endpoint to process incoming Stripe payment webhooks.
    Guest access is required (Stripe can't authenticate as a Frappe user),
    so the HMAC signature check below is the ONLY thing standing between
    this endpoint and anyone on the internet — do not remove it.
    """
    raw_body = frappe.request.get_data()
    sig_header = frappe.get_request_header("Stripe-Signature", "")

    if not _verify_stripe_signature(raw_body, sig_header):
        frappe.local.response.http_status_code = 400
        return {"status": "error", "message": "invalid signature"}

    data = frappe.parse_json(raw_body) or {}
    event_type = data.get("type")

    if event_type == "invoice.payment_succeeded":
        invoice = data.get("data", {}).get("object", {})
        customer_id = invoice.get("customer")

        if not customer_id:
            return {"status": "ignored"}

        # Extract plan nickname/id and resolve it against the known-safe
        # map — an unrecognized nickname is ignored rather than written
        # through to the Subscription doc unchecked.
        lines = invoice.get("lines", {}).get("data", [])
        nickname = None
        if lines and lines[0].get("plan"):
            nickname = lines[0]["plan"].get("nickname")
        plan_id = PLAN_KEY_MAP.get((nickname or "").lower())
        if not plan_id:
            frappe.log_error(f"Unrecognized Stripe plan nickname: {nickname!r}", "Stripe Webhook")
            return {"status": "ignored", "message": "unrecognized plan nickname"}

        # Match strictly on the linked Stripe customer — never fall back to
        # "any active subscription on this site", which would let one
        # customer's webhook event mutate a different customer's plan.
        subscription_name = activate_subscription_for_party(customer_id, plan_id)
        if not subscription_name:
            frappe.log_error(f"No Subscription found for Stripe customer {customer_id}", "Stripe Webhook")
            return {"status": "ignored", "message": "no matching subscription"}

        return {"status": "success", "message": f"Upgraded {subscription_name} to {plan_id}"}

    return {"status": "ignored"}
