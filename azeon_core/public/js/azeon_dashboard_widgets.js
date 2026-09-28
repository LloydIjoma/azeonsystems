// Shared renderers for every azeon_core departmental dashboard Page (see
// azeon_core/page/<name>/). Kept as plain functions on one namespace
// rather than duplicating this HTML-building code six times.
window.azeon_dashboards = window.azeon_dashboards || {};

(function (ns) {
    ns.kpi_grid = function (kpis) {
        var cards = (kpis || []).map(function (k) {
            return (
                '<div class="col-md-3 col-sm-6" style="margin-bottom: 15px;">' +
                    '<div class="frappe-card" style="padding: 18px; border-radius: 8px; border: 1px solid #d1d8dd; border-top: 3px solid ' + (k.color || '#0D47A1') + ';">' +
                        '<div style="font-size: 12px; text-transform: uppercase; color: #6c757d; font-weight: 600;">' + frappe.utils.escape_html(k.label) + '</div>' +
                        '<div style="font-size: 1.6rem; font-weight: 700; margin-top: 6px;">' + k.value + '</div>' +
                    '</div>' +
                '</div>'
            );
        }).join("");
        return '<div class="row">' + cards + '</div>';
    };

    // {label, actual, target, unit, money}
    ns.progress_card = function (t) {
        if (!t) return "";
        var pct = t.target > 0 ? Math.min(100, Math.round((t.actual / t.target) * 100)) : 0;
        var bar_class = pct >= 100 ? "progress-bar-success" : (pct >= 60 ? "progress-bar-info" : "progress-bar-warning");
        var fmt = function (n) { return t.money ? frappe.format(n, { fieldtype: "Currency" }) : n; };
        return (
            '<div class="frappe-card" style="padding: 18px; border-radius: 8px; border: 1px solid #d1d8dd; margin-bottom: 20px;">' +
                '<h5 style="margin-top:0;">' + frappe.utils.escape_html(t.label) + '</h5>' +
                '<p style="color: #6c757d; margin-bottom: 8px;">' + fmt(t.actual) + (t.unit || '') + ' of ' + fmt(t.target) + (t.unit || '') + ' target (' + pct + '%)</p>' +
                '<div class="progress" style="height: 16px;">' +
                    '<div class="progress-bar ' + bar_class + '" role="progressbar" style="width: ' + pct + '%;">' + pct + '%</div>' +
                '</div>' +
            '</div>'
        );
    };

    // {title, headers, rows}
    ns.table_card = function (t) {
        if (!t) return "";
        var thead = (t.headers || []).map(function (h) { return "<th>" + frappe.utils.escape_html(h) + "</th>"; }).join("");
        var body = (t.rows || []).length
            ? t.rows.map(function (r) { return "<tr>" + r.map(function (c) { return "<td>" + c + "</td>"; }).join("") + "</tr>"; }).join("")
            : '<tr><td colspan="' + (t.headers || []).length + '" class="text-center">No records found.</td></tr>';
        return (
            '<div class="frappe-card" style="padding: 20px; border-radius: 8px; border: 1px solid #d1d8dd; margin-bottom: 20px;">' +
                (t.title ? "<h4 style=\"margin-top:0;\">" + frappe.utils.escape_html(t.title) + "</h4>" : "") +
                '<table class="table table-bordered" style="margin-top: 10px;">' +
                    "<thead><tr>" + thead + "</tr></thead><tbody>" + body + "</tbody>" +
                "</table>" +
            "</div>"
        );
    };

    // Buttons that route into a Query Report or a DocType list — built as
    // real DOM nodes with click handlers (not inline onclick strings), so
    // report/doctype names containing spaces or quotes can't break markup.
    ns.action_buttons = function (reports, links) {
        var wrap = document.createElement("div");
        wrap.style.marginBottom = "20px";

        (reports || []).forEach(function (r) {
            var btn = document.createElement("button");
            btn.className = "btn btn-default btn-sm";
            btn.style.marginRight = "8px";
            btn.style.marginBottom = "8px";
            btn.textContent = r.label;
            btn.addEventListener("click", function () {
                frappe.set_route("query-report", r.report);
            });
            wrap.appendChild(btn);
        });

        (links || []).forEach(function (l) {
            var btn = document.createElement("button");
            btn.className = "btn btn-default btn-sm";
            btn.style.marginRight = "8px";
            btn.style.marginBottom = "8px";
            btn.textContent = l.label;
            btn.addEventListener("click", function () {
                frappe.set_route("List", l.doctype);
            });
            wrap.appendChild(btn);
        });

        return wrap;
    };

    // Wires up a standard "load JSON from a whitelisted method, render
    // into page.body" cycle, with a refresh action in the page header.
    ns.load = function (page, method, render_fn) {
        function fetch_and_render() {
            frappe.call({
                method: method,
                callback: function (r) {
                    if (r.message) render_fn(r.message);
                },
            });
        }
        page.set_primary_action(__("Refresh"), fetch_and_render, "octicon octicon-sync");
        fetch_and_render();
    };
})(window.azeon_dashboards);
