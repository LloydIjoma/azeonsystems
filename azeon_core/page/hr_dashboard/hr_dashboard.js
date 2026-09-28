frappe.pages['hr-dashboard'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'HR Dashboard',
        single_column: true,
    });

    azeon_dashboards.load(page, 'azeon_core.dashboards.get_hr_dashboard', function (data) {
        var html = (
            '<div style="padding: 15px;">' +
                azeon_dashboards.kpi_grid(data.kpis) +
                azeon_dashboards.table_card(data.table) +
            '</div>'
        );
        $(page.body).html(html);
        $(page.body).append(azeon_dashboards.action_buttons(data.reports, data.links));
    });
};
