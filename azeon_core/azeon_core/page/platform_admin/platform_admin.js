frappe.pages['platform-admin'] = frappe.pages['platform-admin'] || {};

frappe.pages['platform-admin'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Platform Admin',
		single_column: true
	});

	// Branded logout redirect (Logout -> /admin-login instead of /login) is
	// now handled globally, for every desk page on this site, by
	// public/js/azeon_desk.js — see hooks.py app_include_js / boot_session.

	page.set_primary_action('Refresh', function () {
		load_tenants(page);
	}, 'octicon octicon-sync');

	// Reset Password
	$(page.body).on('click', '.azeon-reset-password-btn', function () {
		var $btn = $(this);
		prompt_reset_password(page, $btn.data('site'), $btn.data('email'));
	});

	// Suspend
	$(page.body).on('click', '.suspend-btn', function () {
		var site = $(this).data('site');
		frappe.confirm(
			__('Are you sure you want to <b>suspend</b> {0}?<br>Users will see the maintenance page.', [
				'<code>' + frappe.utils.escape_html(site) + '</code>'
			]),
			function () {
				frappe.call({
					method: 'azeon_core.platform_admin.suspend_tenant',
					args: { site: site },
					freeze: true,
					freeze_message: __('Suspending tenant...'),
					callback: function (r) {
						if (r.message && r.message.ok) {
							frappe.show_alert({ message: r.message.message, indicator: 'orange' });
							load_tenants(page);
						}
					}
				});
			}
		);
	});

	// Unsuspend
	$(page.body).on('click', '.unsuspend-btn', function () {
		var site = $(this).data('site');
		frappe.confirm(
			__('Unsuspend {0}?', ['<code>' + frappe.utils.escape_html(site) + '</code>']),
			function () {
				frappe.call({
					method: 'azeon_core.platform_admin.unsuspend_tenant',
					args: { site: site },
					freeze: true,
					freeze_message: __('Unsuspending tenant...'),
					callback: function (r) {
						if (r.message && r.message.ok) {
							frappe.show_alert({ message: r.message.message, indicator: 'green' });
							load_tenants(page);
						}
					}
				});
			}
		);
	});

	// Delete — strong confirmation, operator must type the exact site name
	$(page.body).on('click', '.delete-btn', function () {
		var site = $(this).data('site');

		var d = new frappe.ui.Dialog({
			title: __('Delete Tenant — Permanent Action'),
			fields: [
				{
					fieldtype: 'HTML',
					options:
						'<div class="text-danger">' +
						__('This will <b>permanently delete</b> the tenant {0} and its database. A backup will be taken and the site moved to archive.', [
							'<code>' + frappe.utils.escape_html(site) + '</code>'
						]) +
						'<br><br>' + __('Type the exact site name to confirm:') +
						'</div>'
				},
				{
					fieldname: 'confirm_name',
					fieldtype: 'Data',
					label: __('Site Name'),
					reqd: 1
				}
			],
			primary_action_label: __('Delete Forever'),
			primary_action: function (values) {
				if (values.confirm_name !== site) {
					frappe.msgprint(__('Site name does not match. Deletion cancelled.'));
					return;
				}
				d.hide();
				frappe.call({
					method: 'azeon_core.platform_admin.delete_tenant',
					args: { site: site, confirm_site_name: values.confirm_name },
					freeze: true,
					freeze_message: __('Deleting tenant... this may take a minute'),
					callback: function (r) {
						if (r.message && r.message.ok) {
							frappe.show_alert({ message: r.message.message, indicator: 'green' });
							load_tenants(page);
						}
					}
				});
			}
		});
		d.show();
	});

	load_tenants(page);
};

function load_tenants(page) {
	$(page.body).html('<div class="text-muted text-center" style="padding: 40px;">Loading tenants...</div>');

	frappe.call({
		method: 'azeon_core.platform_admin.get_all_tenants',
		freeze: true,
		freeze_message: __('Loading tenants...'),
		callback: function (r) {
			render_tenants(page, r.message || []);
		}
	});
}

function render_tenants(page, tenants) {
	let html = `
		<div class="frappe-card" style="padding: 15px;">
			<h4 style="margin-bottom: 15px;">Tenants (${(tenants || []).length})</h4>
			<table class="table table-bordered table-hover">
				<thead>
					<tr>
						<th>Tenant</th>
						<th>Admin Email</th>
						<th>Created</th>
						<th>Status</th>
						<th style="min-width: 320px;">Actions</th>
					</tr>
				</thead>
				<tbody>
	`;

	if (!tenants || tenants.length === 0) {
		html += `
			<tr>
				<td colspan="5" class="text-muted text-center">No tenants found</td>
			</tr>
		`;
	} else {
		tenants.forEach(tenant => {
			const statusBadge = tenant.is_suspended
				? `<span class="badge badge-warning">Suspended</span>`
				: `<span class="badge badge-success">Active</span>`;

			const suspendBtn = tenant.is_suspended
				? `<button class="btn btn-xs btn-warning unsuspend-btn" data-site="${frappe.utils.escape_html(tenant.site)}">
						Unsuspend
				   </button>`
				: `<button class="btn btn-xs btn-secondary suspend-btn" data-site="${frappe.utils.escape_html(tenant.site)}">
						Suspend
				   </button>`;

			html += `
				<tr>
					<td><strong>${frappe.utils.escape_html(tenant.site)}</strong></td>
					<td>${frappe.utils.escape_html(tenant.admin_email || "—")}</td>
					<td>${frappe.utils.escape_html(tenant.creation || "—")}</td>
					<td>${statusBadge}</td>
					<td>
						<button class="btn btn-xs btn-primary azeon-reset-password-btn"
							data-site="${frappe.utils.escape_html(tenant.site)}"
							data-email="${frappe.utils.escape_html(tenant.admin_email || "")}">
							Reset Password
						</button>
						${suspendBtn}
						<button class="btn btn-xs btn-danger delete-btn"
							data-site="${frappe.utils.escape_html(tenant.site)}">
							Delete
						</button>
						<a class="btn btn-xs btn-default"
						   href="https://${frappe.utils.escape_html(tenant.site)}"
						   target="_blank" rel="noopener">
							Open Site
						</a>
					</td>
				</tr>
			`;
		});
	}

	html += `
				</tbody>
			</table>
		</div>
	`;

	$(page.body).html(html);
}

function prompt_reset_password(page, site, email) {
	frappe.prompt(
		[
			{
				fieldname: 'new_password',
				label: 'New Password',
				fieldtype: 'Password',
				reqd: 1,
				description: __('Minimum 8 characters. The tenant admin will be logged out of all existing sessions.')
			}
		],
		function (values) {
			frappe.confirm(
				__('Reset the password for {0} on {1}? This cannot be undone.', [
					'<b>' + frappe.utils.escape_html(email) + '</b>',
					'<b>' + frappe.utils.escape_html(site) + '</b>'
				]),
				function () {
					frappe.call({
						method: 'azeon_core.platform_admin.reset_tenant_password',
						args: {
							site: site,
							email: email,
							new_password: values.new_password
						},
						freeze: true,
						freeze_message: __('Resetting password...'),
						callback: function (r) {
							if (r.message && r.message.success) {
								frappe.show_alert({
									message: __('Password reset for {0} on {1}.', [email, site]),
									indicator: 'green'
								});
							}
						}
					});
				}
			);
		},
		__('Reset Password — {0}', [site]),
		__('Reset Password')
	);
}
