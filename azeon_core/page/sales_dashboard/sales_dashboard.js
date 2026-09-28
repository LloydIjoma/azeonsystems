frappe.pages['sales-dashboard'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Sales Dashboard',
        single_column: true,
    });

    azeon_dashboards.load(page, 'azeon_core.dashboards.get_sales_dashboard', function (data) {
        var html = (
            '<div style="padding: 15px;">' +
                azeon_dashboards.kpi_grid(data.kpis) +
                azeon_dashboards.progress_card(data.target) +
            '</div>'
        );
        $(page.body).html(html);
        $(page.body).append(azeon_dashboards.action_buttons([], data.links));
    });
};
