frappe.pages['tenant-billing'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Subscription & Billing Portal',
        single_column: true
    });

    page.set_primary_action('Refresh Usage', function() {
        load_billing_data(page);
    }, 'octicon octicon-sync');

    load_billing_data(page);
};

function load_billing_data(page) {
    frappe.call({
        method: 'azeon_core.billing_portal.get_billing_dashboard_data',
        callback: function(r) {
            if (r.message) {
                render_dashboard(page, r.message);
            }
        }
    });
}

function render_dashboard(page, data) {
    let sub = data.subscription;
    let usage = data.usage;
    let inv_rows = data.invoices.map(inv => `
        <tr>
            <td><b>${inv.name}</b></td>
            <td>${inv.posting_date}</td>
            <td>${inv.currency || '$'} ${inv.grand_total}</td>
            <td><span class="indicator-pill ${inv.status === 'Paid' || inv.status === 'Submitted' ? 'green' : 'orange'}">${inv.status}</span></td>
            <td><a href="/api/method/frappe.utils.print_format.download_pdf?doctype=Sales%20Invoice&name=${inv.name}&format=Standard" target="_blank" class="btn btn-default btn-xs">Download PDF</a></td>
        </tr>
    `).join('');

    let html = `
    <div class="billing-container" style="padding: 15px;">
        <!-- Plan Summary Banner -->
        <div class="row">
            <div class="col-md-12">
                <div class="frappe-card" style="padding: 20px; background: #f8f9fa; border-radius: 8px; border: 1px solid #d1d8dd; margin-bottom: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3 style="margin:0;">Current Plan: <span style="color: #2490ef;">${sub.plan_name}</span></h3>
                            <p style="margin: 5px 0 0 0; color: #6c757d;">Subscription Status: <b>${sub.status}</b> | ID: ${sub.subscription_id}</p>
                        </div>
                        <div>
                            <button class="btn btn-primary" onclick="frappe.msgprint('Redirecting to Stripe Customer Portal...')">Upgrade / Change Plan</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Quota Meters -->
        <div class="row">
            <div class="col-md-6">
                <div class="frappe-card" style="padding: 20px; border-radius: 8px; border: 1px solid #d1d8dd; margin-bottom: 20px;">
                    <h4>Storage Quota</h4>
                    <p style="color: #6c757d;">${usage.storage_mb} MB used of ${usage.storage_limit_mb} MB</p>
                    <div class="progress" style="height: 18px;">
                        <div class="progress-bar ${usage.storage_percentage > 85 ? 'progress-bar-danger' : 'progress-bar-info'}" 
                             role="progressbar" style="width: ${usage.storage_percentage}%;">
                            ${usage.storage_percentage}%
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="frappe-card" style="padding: 20px; border-radius: 8px; border: 1px solid #d1d8dd; margin-bottom: 20px;">
                    <h4>Active User Quota</h4>
                    <p style="color: #6c757d;">${usage.active_users} users active of ${usage.user_limit} allowed</p>
                    <div class="progress" style="height: 18px;">
                        <div class="progress-bar ${usage.user_percentage > 85 ? 'progress-bar-warning' : 'progress-bar-success'}" 
                             role="progressbar" style="width: ${usage.user_percentage}%;">
                            ${usage.user_percentage}%
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Invoice Table -->
        <div class="row">
            <div class="col-md-12">
                <div class="frappe-card" style="padding: 20px; border-radius: 8px; border: 1px solid #d1d8dd;">
                    <h4>Payment & Invoice History</h4>
                    <table class="table table-bordered" style="margin-top: 15px;">
                        <thead>
                            <tr>
                                <th>Invoice #</th>
                                <th>Date</th>
                                <th>Amount</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${inv_rows || '<tr><td colspan="5" class="text-center">No invoices found.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    `;

    $(page.body).html(html);
}
