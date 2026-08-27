import frappe
from azeon_core.telemetry import collect_site_metrics
from azeon_core.telemetry_gate import PLAN_LIMITS

@frappe.whitelist()
def get_billing_dashboard_data():
    """
    Returns plan details, active usage metrics, quota caps, and invoice history.
    """
    # 1. Fetch active subscription
    sub_name = frappe.db.get_value("Subscription", {"status": ["in", ["Active", "Trialling"]]}, "name")
    
    current_plan = "Azeon Starter"
    sub_status = "Inactive"
    
    if sub_name:
        sub_doc = frappe.get_doc("Subscription", sub_name)
        sub_status = sub_doc.status
        if sub_doc.plans:
            current_plan = sub_doc.plans[0].plan

    limits = PLAN_LIMITS.get(current_plan, PLAN_LIMITS["Azeon Starter"])
    metrics = collect_site_metrics()

    # Calculate storage & user percentages
    storage_pct = min(100, round((metrics["total_storage_mb"] / limits["max_storage_mb"]) * 100, 1))
    user_pct = min(100, round((metrics["active_users"] / limits["max_users"]) * 100, 1))

    # 2. Fetch recent Sales Invoices
    invoices = frappe.db.get_all(
        "Sales Invoice",
        fields=["name", "posting_date", "grand_total", "status", "currency"],
        order_by="posting_date desc",
        limit=10
    )

    return {
        "subscription": {
            "plan_name": current_plan,
            "status": sub_status,
            "subscription_id": sub_name or "N/A"
        },
        "limits": limits,
        "usage": {
            "storage_mb": metrics["total_storage_mb"],
            "storage_limit_mb": limits["max_storage_mb"],
            "storage_percentage": storage_pct,
            "active_users": metrics["active_users"],
            "user_limit": limits["max_users"],
            "user_percentage": user_pct
        },
        "invoices": invoices
    }
