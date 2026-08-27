frappe.pages['finance-dashboard'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Finance Dashboard',
        single_column: true,
    });

    azeon_dashboards.load(page, 'azeon_core.dashboards.get_finance_dashboard', function (data) {
        var html = '<div style="padding: 15px;">' + azeon_dashboards.kpi_grid(data.kpis) + '</div>';
        $(page.body).html(html);
        $(page.body).append(azeon_dashboards.action_buttons(data.reports, []));
    });
};
