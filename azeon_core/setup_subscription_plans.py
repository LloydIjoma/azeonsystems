import frappe

def create_plans():
    if not frappe.db.exists("UOM", "Nos"):
        uom_doc = frappe.new_doc("UOM")
        uom_doc.uom_name = "Nos"
        uom_doc.insert(ignore_permissions=True)

    if not frappe.db.exists("Item Group", "All Item Groups"):
        group_doc = frappe.new_doc("Item Group")
        group_doc.item_group_name = "All Item Groups"
        group_doc.parent_item_group = ""
        group_doc.is_group = 1
        group_doc.insert(ignore_permissions=True)

    if not frappe.db.exists("Item", "Subscription Item"):
        item_doc = frappe.new_doc("Item")
        item_doc.item_code = "Subscription Item"
        item_doc.item_name = "Subscription Service"
        item_doc.item_group = "All Item Groups"
        item_doc.is_stock_item = 0
        item_doc.stock_uom = "Nos"
        item_doc.insert(ignore_permissions=True)
        print("Created base 'Subscription Item'.")

    plans = [
        {
            "plan_name": "Azeon Starter", 
            "cost": 0, 
            "billing_interval": "Month",
            "item": "Subscription Item",
            "price_determination": "Fixed Rate"
        },
        {
            "plan_name": "Azeon Professional", 
            "cost": 30000, 
            "billing_interval": "Month",
            "item": "Subscription Item",
            "price_determination": "Fixed Rate"
        },
        {
            "plan_name": "Azeon Enterprise", 
            "cost": 50000, 
            "billing_interval": "Month",
            "item": "Subscription Item",
            "price_determination": "Fixed Rate"
        },
    ]

    for plan in plans:
        if not frappe.db.exists("Subscription Plan", plan["plan_name"]):
            doc = frappe.new_doc("Subscription Plan")
            doc.plan_name = plan["plan_name"]
            doc.cost = plan["cost"]
            doc.billing_interval = plan["billing_interval"]
            doc.item = plan["item"]
            doc.price_determination = plan["price_determination"]
            doc.currency = "NGN"
            doc.insert(ignore_permissions=True)
            print(f"Subscription Plan '{plan['plan_name']}' created successfully.")

    frappe.db.commit()
    print("All subscription plans setup complete.")
