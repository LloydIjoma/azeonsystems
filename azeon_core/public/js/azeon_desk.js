frappe.ready(function() {
	// azeon_core is installed on every tenant site as well as the main
	// platform site, so this must only fire where platform_admin_enabled
	// is actually set in site_config (main site only — see
	// azeon_core.platform_admin.add_platform_admin_boot_info, the
	// boot_session hook that populates this flag). On a tenant site
	// frappe.boot.platform_admin_enabled is falsy and this is a no-op, so
	// tenant users keep the default desk logout -> /login behavior.
	if (frappe.boot && frappe.boot.platform_admin_enabled) {
		frappe.app.redirect_to_login = function () {
			window.location.href = '/admin-login';
		};
	}
});
