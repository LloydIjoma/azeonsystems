"""
Azeon Systems — role-based departmental dashboards.

Each function below backs exactly one Page (see azeon_core/page/<name>/)
and returns plain JSON for that page's JS to render via the shared
azeon_dashboard_widgets.js helpers.

A Page's `roles` child table only hides it from the desk sidebar/search
for other roles — it does NOT block a direct API call to the whitelisted
method behind it. So every function here re-checks the caller's role
itself; that check, not the Page's `roles` list, is the real permission
boundary (same principle as the Stripe/Paystack webhook signature checks
elsewhere in this app: the UI-level gate is never the security boundary).

Aggregates use `frappe.db.sql` with bound parameters (never
string-formatted filters) rather than Number Card "Timespan" filter
values, so month-to-date figures are exact regardless of Frappe version.
"""

import frappe
from frappe.utils import today, get_first_day, get_last_day, fmt_money


def _require_role(*roles):
    """
    Allow System Manager, Azeon Tenant Admin (the tenant's own
    super-admins), and Azeon Manager (a cross-department viewer with no
    single department's head role — see utils/roles.py) on every
    dashboard, plus whichever department role(s) the caller passes in.
    """
    allowed = set(roles) | {"System Manager", "Azeon Tenant Admin", "Azeon Manager"}
    if allowed.isdisjoint(frappe.get_roles(frappe.session.user)):
        frappe.throw(
            f"You need one of these roles to view this dashboard: {', '.join(roles)}.",
            frappe.PermissionError,
        )


def _sum(doctype, field, conditions, values):
    """SUM(field) over doctype with hand-built, parameterized WHERE
    conditions — used instead of frappe.db.get_value's own aggregate
    shorthand so date-range conditions stay explicit and easy to audit."""
    where = " and ".join(conditions) if conditions else "1=1"
    result = frappe.db.sql(f"select sum({field}) from `tab{doctype}` where {where}", values)
    return float(result[0][0] or 0) if result and result[0] else 0.0


def _count(doctype, filters):
    return frappe.db.count(doctype, filters)


@frappe.whitelist()
def get_manager_dashboard():
    """Consolidated cross-department view for business managers/CEOs."""
    _require_role("Sales Manager", "Accounts Manager", "HR Manager", "Purchase Manager", "Stock Manager")

    month_start, month_end = get_first_day(today()), get_last_day(today())
    sales_today = _sum("Sales Invoice", "base_grand_total", ["docstatus = 1", "posting_date = %s"], [today()])
    revenue_mtd = _sum("Sales Invoice", "base_grand_total",
                        ["docstatus = 1", "posting_date between %s and %s"], [month_start, month_end])
    expenses_mtd = _sum("Purchase Invoice", "base_grand_total",
                         ["docstatus = 1", "posting_date between %s and %s"], [month_start, month_end])

    return {
        "title": "Manager Dashboard",
        "kpis": [
            {"label": "Sales Today", "value": fmt_money(sales_today), "color": "#F57C00"},
            {"label": "Revenue (MTD)", "value": fmt_money(revenue_mtd), "color": "#0D47A1"},
            {"label": "Expenses (MTD)", "value": fmt_money(expenses_mtd), "color": "#0D47A1"},
            {"label": "Gross Profit (MTD, est.)", "value": fmt_money(revenue_mtd - expenses_mtd), "color": "#F57C00"},
            {"label": "Active Leads", "value": _count("Lead", {"status": ["not in", ["Converted", "Do Not Contact"]]}), "color": "#0D47A1"},
            {"label": "Open Sales Orders", "value": _count("Sales Order", {"docstatus": 1, "status": ["not in", ["Completed", "Closed", "Cancelled"]]}), "color": "#F57C00"},
            {"label": "Pending Purchase Orders", "value": _count("Purchase Order", {"docstatus": 1, "status": ["not in", ["Completed", "Closed", "Cancelled"]]}), "color": "#0D47A1"},
            {"label": "Employees on Leave Today", "value": _count("Leave Application", {"status": "Approved", "docstatus": 1, "from_date": ["<=", today()], "to_date": [">=", today()]}), "color": "#F57C00"},
            {"label": "Low Stock Items", "value": _count("Bin", {"actual_qty": ["<=", 10]}), "color": "#0D47A1"},
        ],
        # Gross profit above is an estimate (Sales - Purchase invoices for
        # the month) -- link out to ERPNext's real, accounting-correct P&L
        # and Balance Sheet rather than trying to reproduce them as a
        # single number.
        "reports": [
            {"label": "Profit and Loss Statement", "report": "Profit and Loss Statement"},
            {"label": "Balance Sheet", "report": "Balance Sheet"},
        ],
    }


@frappe.whitelist()
def get_sales_dashboard():
    _require_role("Sales Manager", "Sales User")

    month_start, month_end = get_first_day(today()), get_last_day(today())
    actual_mtd = _sum("Sales Invoice", "base_grand_total",
                       ["docstatus = 1", "posting_date between %s and %s"], [month_start, month_end])
    target = frappe.db.get_single_value("Azeon Settings", "monthly_sales_target") or 0

    return {
        "title": "Sales Dashboard",
        "kpis": [
            {"label": "New Leads Today", "value": _count("Lead", {"creation": [">=", today()]}), "color": "#F57C00"},
            {"label": "Sales Completed Today", "value": _count("Sales Invoice", {"docstatus": 1, "posting_date": today()}), "color": "#0D47A1"},
            {"label": "Open Opportunities", "value": _count("Opportunity", {"status": ["not in", ["Lost", "Closed", "Converted"]]}), "color": "#F57C00"},
        ],
        "target": {"label": "Sales Target (Month to Date)", "actual": actual_mtd, "target": target, "unit": "", "money": True},
        "links": [{"label": "Sales Order List", "doctype": "Sales Order"}],
    }


@frappe.whitelist()
def get_marketing_dashboard():
    _require_role("Sales Manager", "Sales User")

    month_start = get_first_day(today())
    leads_mtd = _count("Lead", {"creation": [">=", month_start]})
    target = frappe.db.get_single_value("Azeon Settings", "monthly_lead_target") or 0

    campaigns = frappe.db.sql(
        """
        select campaign_name, count(*) as lead_count
        from `tabLead`
        where campaign_name is not null and campaign_name != ''
        group by campaign_name
        order by lead_count desc
        limit 10
        """,
        as_dict=True,
    )

    return {
        "title": "Marketing Dashboard",
        "kpis": [
            {"label": "New Leads (MTD)", "value": leads_mtd, "color": "#F57C00"},
            {"label": "Active Campaigns", "value": _count("Campaign", {}), "color": "#0D47A1"},
        ],
        "target": {"label": "Lead Generation Target (MTD)", "actual": leads_mtd, "target": target, "unit": " leads"},
        "campaigns": campaigns,
        "links": [
            {"label": "Contact List", "doctype": "Contact"},
            {"label": "Lead List", "doctype": "Lead"},
        ],
    }


@frappe.whitelist()
def get_finance_dashboard():
    _require_role("Accounts Manager", "Accounts User")

    month_start, month_end = get_first_day(today()), get_last_day(today())
    receivables = _sum("Sales Invoice", "outstanding_amount", ["docstatus = 1", "outstanding_amount > 0"], [])
    payables = _sum("Purchase Invoice", "outstanding_amount", ["docstatus = 1", "outstanding_amount > 0"], [])
    income_mtd = _sum("Sales Invoice", "base_grand_total",
                       ["docstatus = 1", "posting_date between %s and %s"], [month_start, month_end])
    expense_mtd = _sum("Purchase Invoice", "base_grand_total",
                        ["docstatus = 1", "posting_date between %s and %s"], [month_start, month_end])

    return {
        "title": "Finance Dashboard",
        "kpis": [
            {"label": "Total Receivables", "value": fmt_money(receivables), "color": "#0D47A1"},
            {"label": "Total Payables", "value": fmt_money(payables), "color": "#F57C00"},
            {"label": "Income (MTD)", "value": fmt_money(income_mtd), "color": "#0D47A1"},
            {"label": "Expenses (MTD)", "value": fmt_money(expense_mtd), "color": "#F57C00"},
        ],
        # Balance sheet visibility is deliberately a link, not a
        # reproduced number -- it depends on account trees / opening
        # balances that only ERPNext's own report computes correctly.
        "reports": [
            {"label": "Balance Sheet", "report": "Balance Sheet"},
            {"label": "Profit and Loss Statement", "report": "Profit and Loss Statement"},
            {"label": "General Ledger", "report": "General Ledger"},
        ],
    }


@frappe.whitelist()
def get_hr_dashboard():
    _require_role("HR Manager", "HR User")

    month_start = get_first_day(today())
    promotions = frappe.get_all(
        "Employee Promotion",
        filters={"docstatus": 1, "promotion_date": [">=", month_start]},
        fields=["employee_name", "promotion_date"],
        order_by="promotion_date desc",
        limit=10,
    )

    return {
        "title": "HR Dashboard",
        "kpis": [
            {"label": "Present Today", "value": _count("Attendance", {"docstatus": 1, "attendance_date": today(), "status": "Present"}), "color": "#0D47A1"},
            {"label": "Absent Today", "value": _count("Attendance", {"docstatus": 1, "attendance_date": today(), "status": "Absent"}), "color": "#F57C00"},
            {"label": "On Leave Today", "value": _count("Leave Application", {"status": "Approved", "docstatus": 1, "from_date": ["<=", today()], "to_date": [">=", today()]}), "color": "#0D47A1"},
            {"label": "Pending Leave Approvals", "value": _count("Leave Application", {"status": "Open"}), "color": "#F57C00"},
        ],
        "table": {
            "title": "Recent Promotions (This Month)",
            "headers": ["Employee", "Promotion Date"],
            "rows": [[p.employee_name, frappe.utils.formatdate(p.promotion_date)] for p in promotions],
        },
        # Leave balance is per-employee, per-leave-type -- a single
        # aggregate number would hide more than it shows, so link to
        # ERPNext's own report instead.
        "reports": [{"label": "Employee Leave Balance", "report": "Employee Leave Balance"}],
        "links": [{"label": "Leave Application List", "doctype": "Leave Application"}],
    }


@frappe.whitelist()
def get_procurement_dashboard():
    _require_role("Purchase Manager", "Stock Manager", "Stock User")

    total_stock_value = _sum("Bin", "stock_value", [], [])

    return {
        "title": "Procurement & Inventory Dashboard",
        "kpis": [
            {"label": "Low Stock Items", "value": _count("Bin", {"actual_qty": ["<=", 10]}), "color": "#F57C00"},
            {"label": "Total Inventory Value", "value": fmt_money(total_stock_value), "color": "#0D47A1"},
            {"label": "Pending Purchase Requests", "value": _count("Material Request", {
                "docstatus": 1,
                "status": ["not in", ["Stopped", "Cancelled", "Ordered", "Received", "Issued", "Transferred"]],
            }), "color": "#F57C00"},
            {"label": "Open Purchase Orders", "value": _count("Purchase Order", {"docstatus": 1, "status": ["not in", ["Completed", "Closed", "Cancelled"]]}), "color": "#0D47A1"},
        ],
        "reports": [{"label": "Stock Balance", "report": "Stock Balance"}],
        "links": [
            {"label": "Material Request List", "doctype": "Material Request"},
            {"label": "Purchase Order List", "doctype": "Purchase Order"},
        ],
    }
