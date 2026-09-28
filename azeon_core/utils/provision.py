import frappe
from frappe.utils import nowdate
from frappe.utils.password import update_password


def _ensure_billing_customer(name):
    if not frappe.db.exists("Customer Group", "All Customer Groups"):
        group_doc = frappe.new_doc("Customer Group")
        group_doc.customer_group_name = "All Customer Groups"
        group_doc.parent_customer_group = ""
        group_doc.is_group = 1
        group_doc.insert(ignore_permissions=True)

    if not frappe.db.exists("Customer Group", "Commercial"):
        sub_group = frappe.new_doc("Customer Group")
        sub_group.customer_group_name = "Commercial"
        sub_group.parent_customer_group = "All Customer Groups"
        sub_group.is_group = 0
        sub_group.insert(ignore_permissions=True)

    if not frappe.db.exists("Territory", "All Territories"):
        territory_doc = frappe.new_doc("Territory")
        territory_doc.territory_name = "All Territories"
        territory_doc.parent_territory = ""
        territory_doc.is_group = 1
        territory_doc.insert(ignore_permissions=True)

    customer_name = f"{name} (Billing)"
    if frappe.db.exists("Customer", customer_name):
        cust_doc = frappe.get_doc("Customer", customer_name)
        if cust_doc.default_currency != "NGN":
            cust_doc.default_currency = "NGN"
            cust_doc.save(ignore_permissions=True)
        return customer_name

    customer = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": customer_name,
        "customer_type": "Company",
        "customer_group": "Commercial",
        "territory": "All Territories",
        "default_currency": "NGN"
    })
    customer.insert(ignore_permissions=True)
    return customer.name


def _set_company_currency_to_ngn():
    companies = frappe.get_all("Company", pluck="name")
    for company_name in companies:
        company_doc = frappe.get_doc("Company", company_name)
        if company_doc.default_currency != "NGN":
            company_doc.default_currency = "NGN"
            company_doc.save(ignore_permissions=True)
    frappe.db.commit()


def _create_subscription(customer, plan_key):
    plan_mapping = {
        "starter": "Azeon Starter",
        "professional": "Azeon Professional",
        "enterprise": "Azeon Enterprise"
    }
    if plan_key.lower() == "custom":
        print("Custom plan selected. Skipping automated subscription creation.")
        return None

    plan_name = plan_mapping.get(plan_key.lower(), "Azeon Starter")
    existing = frappe.db.exists("Subscription", {
        "party": customer,
        "status": ["in", ["Active", "Trialing"]]
    })
    if existing:
        print(f"Active subscription '{existing}' already exists for customer.")
        return existing

    sub = frappe.new_doc("Subscription")
    sub.party_type = "Customer"
    sub.party = customer
    sub.start_date = nowdate()
    sub.append("plans", {
        "plan": plan_name,
        "qty": 1
    })
    sub.insert(ignore_permissions=True)
    sub.submit()
    print(f"Subscription '{plan_name}' created and submitted successfully.")
    return sub.name


def _set_admin_email(admin_email):
    if not admin_email:
        return
    if frappe.db.get_value("User", "Administrator", "email") != admin_email:
        frappe.db.set_value("User", "Administrator", "email", admin_email)
        frappe.db.commit()


def _create_tenant_admin_user(admin_email, admin_password, company_name=None):
    if not admin_email or not admin_password:
        print("Skipping tenant admin user creation – missing email or password")
        return None

    if frappe.db.exists("User", admin_email):
        user = frappe.get_doc("User", admin_email)
        update_password(user.name, admin_password)
        user.enabled = 1
        user.save(ignore_permissions=True)
        user.add_roles("System Manager", "All")
        frappe.db.commit()
        print(f"Updated existing user '{admin_email}' and set password")
        return user.name

    first_name = (company_name or admin_email.split("@")[0]).strip()[:30] or "Admin"

    user = frappe.get_doc({
        "doctype": "User",
        "email": admin_email,
        "first_name": first_name,
        "enabled": 1,
        "send_welcome_email": 0,
        "user_type": "System User",
    })
    user.insert(ignore_permissions=True)
    update_password(user.name, admin_password)
    user.add_roles("System Manager", "All")
    frappe.db.commit()
    print(f"Created tenant admin user '{admin_email}' with System Manager role")
    return user.name


def _complete_setup_wizard(company_name):
    """Skip the ERPNext setup wizard so new tenants land in the desk."""
    try:
        if not company_name:
            company_name = "My Company"

        # Ensure a Company exists
        if not frappe.db.exists("Company", company_name):
            abbr = "".join([c[0] for c in company_name.split() if c][:3]).upper() or "CO"
            # Make abbr unique if needed
            base_abbr = abbr
            i = 1
            while frappe.db.exists("Company", {"abbr": abbr}):
                abbr = f"{base_abbr}{i}"
                i += 1

            company = frappe.get_doc({
                "doctype": "Company",
                "company_name": company_name,
                "abbr": abbr,
                "default_currency": "NGN",
                "country": "Nigeria",
            })
            company.insert(ignore_permissions=True)
            print(f"Created Company '{company_name}'")

        # Mark setup as complete
        frappe.db.set_single_value("System Settings", "setup_complete", 1)
        frappe.db.set_single_value("System Settings", "country", "Nigeria")
        frappe.db.set_single_value("System Settings", "time_zone", "Africa/Lagos")
        frappe.db.set_single_value("System Settings", "language", "en")
        frappe.db.commit()
        print(f"Setup wizard marked complete for {company_name}")
    except Exception as e:
        print(f"Could not complete setup wizard: {e}")


def _send_welcome_email(admin_email, company_name, site_name):
    if not admin_email:
        return

    workspace_url = f"https://{site_name}"
    subject = f"Your Azeon Systems workspace is ready – {company_name or site_name}"

    message = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: #1a1a2e;">Welcome to Azeon Systems</h2>
      <p>Hi,</p>
      <p>Your workspace for <strong>{company_name or site_name}</strong> has been successfully provisioned.</p>
      <p>
        <a href="{workspace_url}"
           style="display:inline-block;padding:12px 24px;background:#f97316;color:#fff;
                  text-decoration:none;border-radius:6px;font-weight:bold;">
          Go to your workspace
        </a>
      </p>
      <p style="margin-top:24px;">
        <strong>Login details</strong><br>
        URL: <a href="{workspace_url}">{workspace_url}</a><br>
        Email: {admin_email}<br>
        Password: the one you chose during registration
      </p>
      <p style="color:#666;font-size:13px;margin-top:32px;">
        If you did not request this workspace, please ignore this email.
      </p>
    </div>
    """

    try:
        frappe.sendmail(
            recipients=[admin_email],
            subject=subject,
            message=message,
            now=True,
        )
        print(f"Welcome email sent to {admin_email}")
    except Exception as e:
        print(f"Could not send welcome email: {e}")


def bootstrap_tenant(company_name, admin_email, plan='starter', admin_password=None):
    from azeon_core.setup_subscription_plans import create_plans

    create_plans()
    _set_admin_email(admin_email)
    _create_tenant_admin_user(admin_email, admin_password, company_name)
    _complete_setup_wizard(company_name or (admin_email.split("@")[0] if admin_email else "My Company"))
    _set_company_currency_to_ngn()
    customer = _ensure_billing_customer(company_name or admin_email)
    print(f"Billing customer '{customer}' ensured successfully.")
    subscription = _create_subscription(customer, plan)
    print(f"Tenant successfully bootstrapped with subscription: {subscription}")
    site_name = frappe.local.site
    _send_welcome_email(admin_email, company_name, site_name)
    return customer
