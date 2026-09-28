frappe.pages['marketing-dashboard'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Marketing Dashboard',
        single_column: true,
    });

    azeon_dashboards.load(page, 'azeon_core.dashboards.get_marketing_dashboard', function (data) {
        var campaign_table = azeon_dashboards.table_card({
            title: 'Campaign Performance (by Leads Generated)',
            headers: ['Campaign', 'Leads'],
            rows: (data.campaigns || []).map(function (c) { return [c.campaign_name, c.lead_count]; }),
        });

        var html = (
            '<div style="padding: 15px;">' +
                azeon_dashboards.kpi_grid(data.kpis) +
                azeon_dashboards.progress_card(data.target) +
                campaign_table +
            '</div>'
        );
        $(page.body).html(html);
        $(page.body).append(azeon_dashboards.action_buttons([], data.links));
    });
};
