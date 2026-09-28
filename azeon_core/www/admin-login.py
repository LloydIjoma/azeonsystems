import frappe

no_cache = 1


def get_context(context):
	"""
	/admin-login is a standalone, branded login screen for the platform
	owner only. If the visitor already has a valid session we skip the form
	entirely: System Managers with platform_admin_enabled go straight to
	Platform Admin, everyone else goes to their normal desk — nobody should
	be shown (or asked to re-enter credentials into) an "admin login" form
	that isn't for them.
	"""
	if frappe.session.user and frappe.session.user != "Guest":
		if frappe.conf.get("platform_admin_enabled") and "System Manager" in frappe.get_roles():
			frappe.local.flags.redirect_location = "/app/platform-admin"
		else:
			frappe.local.flags.redirect_location = "/app"
		raise frappe.Redirect
