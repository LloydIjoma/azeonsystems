import frappe

# Prices match the public pricing page (frontend/src/components/PricingTable.tsx).
# Professional and Enterprise are priced per user/month: `cost` here is the
# per-seat rate, and the Subscription's `plans` child-table row for a given
# tenant should have its `qty` set to that tenant's active user count so
# Frappe's Subscription (cost x qty) billing comes out to the advertised
# per-user price. Starter is flat ($0) regardless of seat count. "Custom" is
# intentionally not a Subscription Plan record — it's sales-negotiated, not
# self-serve.
def create_plans():
    plans = [
        {"plan_name": "Azeon Starter", "cost": 0, "billing_interval": "Month"},
        {"plan_name": "Azeon Professional", "cost": 15, "billing_interval": "Month"},
        {"plan_name": "Azeon Enterprise", "cost": 59, "billing_interval": "Month"},
    ]

    for plan in plans:
        if not frappe.db.exists("Subscription Plan", plan["plan_name"]):
            doc = frappe.new_doc("Subscription Plan")
            doc.plan_name = plan["plan_name"]
            doc.cost = plan["cost"]
            doc.billing_interval = plan["billing_interval"]
            doc.currency = "USD"
            doc.insert(ignore_permissions=True)
            print(f"Subscription Plan '{plan['plan_name']}' created successfully.")
    
    frappe.db.commit()
    print("All subscription plans setup complete.")
