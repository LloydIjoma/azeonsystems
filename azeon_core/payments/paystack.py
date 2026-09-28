"""
Azeon Systems — Paystack payment integration.

Paystack is the primary Nigerian-market payment processor here: it covers
local debit/credit cards, bank transfers, and USSD, and its transactions
API supports NGN-native recurring billing. This is a SKELETON — set
`paystack_secret_key` in every tenant's site_config.json (Paystack
dashboard > Settings > API Keys & Webhooks) and register the webhook URL
below there before enabling it for real traffic.

Flow:
  1. A logged-in tenant user clicks a paid tier's "Upgrade" button on
     /pricing, which calls `initialize_transaction(plan)`. That looks up
     the plan's real price server-side (never trust a client-supplied
     amount — see invoice_generator.py for the bug this avoids), and asks
     Paystack to open a transaction; the browser is redirected to the
     returned `authorization_url`.
  2. Paystack collects payment on its own hosted page — no card data ever
     touches this server, so it stays out of PCI scope.
  3. Paystack calls `paystack_webhook()` (HMAC-verified) with the result.
     On `charge.success` we activate the tenant's Subscription for the
     plan that was paid for, via the same subscription_gate helper the
     Stripe integration uses, so gating (PLAN_MODULE_MAP) takes effect
     immediately either way.

Webhook URL to register in the Paystack dashboard:
  https://{tenant_slug}.azeonsystems.com.ng/api/method/azeon_core.payments.paystack.paystack_webhook

Flutterwave is the other common Nigerian-market processor. It can be wired
in as a sibling `flutterwave.py` module using this same shape:
`initialize_transaction` + a `flutterwave_webhook` verified against the
`verif-hash` header (Flutterwave's equivalent of Paystack's HMAC check).
"""

import hashlib
import hmac

import frappe
import requests

from azeon_core.subscription_gate import PLAN_KEY_MAP, activate_subscription_for_party

PAYSTACK_BASE_URL = "https://api.paystack.co"


def _secret_key():
    key = frappe.conf.get("paystack_secret_key")
    if not key:
        frappe.throw("paystack_secret_key is not configured in site_config.json.")
    return key


def _resolve_customer():
    """Resolve the Customer linked to the logged-in session user — never
    take a customer identity from request input."""
    customer = frappe.db.get_value(
        "Contact Link", {"parenttype": "Contact", "link_doctype": "Customer"}, "link_name"
    )
    if not customer:
        frappe.throw("No customer record is linked to your account.", frappe.PermissionError)
    return customer


@frappe.whitelist()
def initialize_transaction(plan):
    """
    Starts a Paystack Checkout for the calling user's own customer record,
    for one of the self-serve plans (starter/professional/enterprise —
    same keys the frontend pricing page and signup form use). Returns the
    `authorization_url` to redirect the browser to; Paystack collects
    payment and confirms asynchronously via `paystack_webhook`.
    """
    plan_name = PLAN_KEY_MAP.get((plan or "").lower())
    if not plan_name:
        frappe.throw(f"Unknown plan: {plan}")

    rate = frappe.db.get_value("Subscription Plan", plan_name, "cost")
    if rate is None:
        frappe.throw(f"Subscription plan '{plan_name}' has no configured cost.")
    if rate <= 0:
        frappe.throw("This plan does not require payment.")

    customer = _resolve_customer()
    # Falls back to the session user's login, which for a portal user is
    # already their email address — a real deployment should prefer a
    # verified email field on Customer/Contact once one is modeled.
    email = frappe.db.get_value("Customer", customer, "email_id") or frappe.session.user

    payload = {
        "email": email,
        # Paystack amounts are in the smallest currency unit (kobo for NGN).
        "amount": int(round(rate * 100)),
        "currency": frappe.conf.get("paystack_currency", "NGN"),
        "callback_url": f"{frappe.utils.get_url()}/pricing?checkout=complete",
        "metadata": {
            "customer": customer,
            "plan": plan,
            "plan_name": plan_name,
        },
    }

    try:
        resp = requests.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            json=payload,
            headers={"Authorization": f"Bearer {_secret_key()}"},
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        frappe.log_error(f"Paystack initialize failed: {exc}", "Paystack")
        frappe.throw("Could not start checkout with Paystack. Please try again shortly.")

    data = resp.json()
    if not data.get("status"):
        frappe.log_error(f"Paystack initialize rejected: {data}", "Paystack")
        frappe.throw(data.get("message") or "Paystack rejected the checkout request.")

    return {
        "authorization_url": data["data"]["authorization_url"],
        "reference": data["data"]["reference"],
    }


def _verify_paystack_signature(raw_body: bytes, signature: str) -> bool:
    """
    Paystack signs webhook payloads as HMAC-SHA512 of the raw body, keyed
    by the SAME secret key used for API calls (no separate webhook secret)
    — see https://paystack.com/docs/payments/webhooks/.
    """
    if not signature:
        return False
    expected = hmac.new(_secret_key().encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


@frappe.whitelist(allow_guest=True)
def paystack_webhook():
    """
    Guest-accessible endpoint Paystack calls on payment events. Guest
    access is required (Paystack can't authenticate as a Frappe user), so
    the HMAC signature check below is the ONLY thing standing between this
    endpoint and anyone on the internet — do not remove it.
    """
    raw_body = frappe.request.get_data()
    signature = frappe.get_request_header("x-paystack-signature", "")

    if not _verify_paystack_signature(raw_body, signature):
        frappe.local.response.http_status_code = 400
        return {"status": "error", "message": "invalid signature"}

    data = frappe.parse_json(raw_body) or {}
    event = data.get("event")
    charge = data.get("data") or {}
    metadata = charge.get("metadata") or {}

    if event == "charge.success":
        customer = metadata.get("customer")
        plan_name = metadata.get("plan_name")

        if not customer or plan_name not in PLAN_KEY_MAP.values():
            frappe.log_error(f"Paystack charge.success with unusable metadata: {metadata}", "Paystack Webhook")
            return {"status": "ignored"}

        subscription_name = activate_subscription_for_party(customer, plan_name)
        if not subscription_name:
            frappe.log_error(f"No Subscription found for customer {customer}", "Paystack Webhook")
            return {"status": "ignored", "message": "no matching subscription"}

        return {"status": "success", "message": f"Upgraded {subscription_name} to {plan_name}"}

    if event == "charge.failed":
        frappe.log_error(f"Paystack charge failed: reference={charge.get('reference')}", "Paystack Webhook")
        return {"status": "acknowledged"}

    # subscription.create / subscription.disable / invoice.* etc. are not
    # acted on yet — acknowledge so Paystack doesn't retry, but leave a
    # trace so it's visible this event type is still unhandled.
    return {"status": "ignored", "event": event}
