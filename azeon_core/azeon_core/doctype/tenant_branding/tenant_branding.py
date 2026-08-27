import frappe
from frappe.model.document import Document

class TenantBranding(Document):
    def validate(self):
        # Prevent secondary entries
        if not self.is_new() and frappe.db.exists("Tenant Branding", {"name": ["!=", self.name]}):
            frappe.throw("Only one Tenant Branding configuration is allowed per site.")

    def on_update(self):
        self.apply_branding_and_security()

    def apply_branding_and_security(self):
        # 1. Update Site Website Settings (App Name & Logo)
        ws = frappe.get_doc("Website Settings", "Website Settings")
        if self.app_name:
            ws.app_name = self.app_name
        if self.app_logo:
            ws.app_logo = self.app_logo
        if self.favicon:
            ws.favicon = self.favicon
        if self.email_footer:
            ws.footer_powered = self.email_footer
        ws.save(ignore_permissions=True)

        # 2. Enforce System Manager Two-Factor Authentication (2FA)
        if self.enforce_mfa:
            frappe.db.set_value("System Settings", None, "enable_two_factor_auth", 1)
        
        frappe.db.commit()
        frappe.clear_cache()
