import frappe
from azeon_core.telemetry import collect_site_metrics

# Plan thresholds in MB / Users. Must stay in sync with subscription_gate's
# PLAN_MODULE_MAP — a plan missing here silently falls back to the Starter
# limits below (see the .get(..., PLAN_LIMITS["Azeon Starter"]) call sites),
# which previously under-capped every "Azeon Enterprise" tenant.
PLAN_LIMITS = {
    "Azeon 7-Day Trial": {"max_storage_mb": 500, "max_users": 3},
    "Azeon Starter": {"max_storage_mb": 500, "max_users": 3},
    "Azeon Professional": {"max_storage_mb": 10000, "max_users": 15},
    "Azeon Enterprise": {"max_storage_mb": 50000, "max_users": 50},
}

def validate_tenant_limits():
    """
    Checks site metrics against current active plan limit.
    """
    sub = frappe.db.get_value("Subscription", {"status": "Active"}, ["name"], as_dict=True)
    if not sub:
        return

    sub_doc = frappe.get_doc("Subscription", sub.name)
    plan_name = sub_doc.plans[0].plan if sub_doc.plans else "Azeon Starter"
    limits = PLAN_LIMITS.get(plan_name, PLAN_LIMITS["Azeon Starter"])

    metrics = collect_site_metrics()

    if metrics["total_storage_mb"] > limits["max_storage_mb"]:
        frappe.log_error(
            f"Storage limit exceeded: {metrics['total_storage_mb']}MB / {limits['max_storage_mb']}MB",
            "Tenant Limit Exception"
        )
        return {"status": "warning", "reason": "storage_exceeded"}

    return {"status": "ok", "metrics": metrics}
