"""
Azeon Systems — CEO Performance Dashboard bootstrap.

Builds the Number Cards, Dashboard Chart, and Workspace that make up the
default "CEO Dashboard" every tenant gets on install. Entry point is
`after_install`, wired via azeon_core/hooks.py.

Version-sensitivity note: the Workspace `content` block schema below
targets Frappe's v14/v15 Workspace editor. If the bench this runs against
is on a materially different framework version, re-verify the block shape
against that version's Workspace doctype before relying on this in
production.
"""

import frappe

from azeon_core.setup_notifications import create_invoice_notification
from azeon_core.setup_subscription_plans import create_plans
from azeon_core.utils.roles import create_tenant_roles

# Simplification: a fixed low-stock threshold across all items/warehouses,
# because a true per-item reorder-level comparison needs a script report,
# not a plain Number Card filter. Tune this (or replace the card with a
# proper report-based one) per tenant after go-live.
LOW_STOCK_THRESHOLD = 10

CEO_WORKSPACE_LABEL = "CEO Dashboard"
SALES_TREND_CHART_LABEL = "Sales Revenue Trend"

NAVY = "#0D47A1"
ORANGE = "#F57C00"

NUMBER_CARDS = [
    {
        "label": "Daily Sales Revenue",
        "document_type": "Sales Invoice",
        "function": "Sum",
        "aggregate_function_based_on": "base_grand_total",
        "filters": [
            ["Sales Invoice", "docstatus", "=", 1],
            ["Sales Invoice", "posting_date", "=", "Today"],
        ],
        "color": NAVY,
    },
    {
        "label": "Active Leads",
        "document_type": "Lead",
        "function": "Count",
        "aggregate_function_based_on": None,
        "filters": [
            ["Lead", "status", "not in", ["Converted", "Do Not Contact"]],
        ],
        "color": ORANGE,
    },
    {
        "label": "Sales Pipeline Value",
        "document_type": "Opportunity",
        "function": "Sum",
        "aggregate_function_based_on": "opportunity_amount",
        "filters": [
            ["Opportunity", "status", "not in", ["Lost", "Closed", "Converted"]],
        ],
        "color": ORANGE,
    },
    {
        "label": "Warehouse Inventory Value",
        "document_type": "Bin",
        "function": "Sum",
        "aggregate_function_based_on": "stock_value",
        "filters": [],
        "color": NAVY,
    },
    {
        "label": "Low Stock Items",
        "document_type": "Bin",
        "function": "Count",
        "aggregate_function_based_on": None,
        "filters": [
            ["Bin", "actual_qty", "<=", LOW_STOCK_THRESHOLD],
        ],
        "color": ORANGE,
    },
    {
        "label": "Unpaid Invoices",
        "document_type": "Sales Invoice",
        "function": "Sum",
        "aggregate_function_based_on": "outstanding_amount",
        "filters": [
            ["Sales Invoice", "status", "in", ["Unpaid", "Overdue", "Partly Paid"]],
        ],
        "color": NAVY,
    },
]


def after_install():
    """
    Runs once, right after `bench --site <site> install-app azeon_core`.

    Each stage is isolated: a failure in one (building a card, creating
    tenant roles, seeding subscription plans, ...) is logged via
    frappe.log_error rather than raised, so one schema mismatch or one
    already-customized doctype can't fail the whole tenant provisioning
    run (the site and ERPNext are already installed by this point).
    """
    frappe.logger("azeon_core").info("Running azeon_core after_install")

    stages = (
        create_number_cards,
        create_sales_trend_chart,
        create_ceo_workspace,
        create_tenant_roles,
        create_invoice_notification,
        create_plans,
    )
    for stage in stages:
        try:
            stage()
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(
                title=f"azeon_core after_install: {stage.__name__} failed",
                message=frappe.get_traceback(),
            )

    frappe.clear_cache()


def create_number_cards():
    for card in NUMBER_CARDS:
        if frappe.db.exists("Number Card", card["label"]):
            continue

        doc = frappe.new_doc("Number Card")
        doc.label = card["label"]
        doc.document_type = card["document_type"]
        doc.function = card["function"]
        if card["aggregate_function_based_on"]:
            doc.aggregate_function_based_on = card["aggregate_function_based_on"]
        doc.filters_json = frappe.as_json(card["filters"])
        doc.is_public = 1
        doc.color = card["color"]
        doc.insert(ignore_permissions=True)


def create_sales_trend_chart():
    if frappe.db.exists("Dashboard Chart", SALES_TREND_CHART_LABEL):
        return

    doc = frappe.new_doc("Dashboard Chart")
    doc.chart_name = SALES_TREND_CHART_LABEL
    doc.chart_type = "Sum"
    doc.document_type = "Sales Invoice"
    doc.based_on = "posting_date"
    doc.value_based_on = "base_grand_total"
    doc.time_interval = "Daily"
    doc.timespan = "Last Month"
    doc.type = "Line"
    doc.color = NAVY
    doc.is_public = 1
    doc.filters_json = frappe.as_json([["Sales Invoice", "docstatus", "=", 1]])
    doc.insert(ignore_permissions=True)


def create_ceo_workspace():
    if frappe.db.exists("Workspace", CEO_WORKSPACE_LABEL):
        return

    def block(block_type, data):
        return {"id": frappe.generate_hash(length=10), "type": block_type, "data": data}

    content = [
        block("header", {
            "text": '<span class="h4"><b>CEO Performance Dashboard</b></span>',
            "col": 12,
        }),
    ]
    for card in NUMBER_CARDS:
        content.append(block("number_card", {"number_card_name": card["label"], "col": 4}))
    content.append(block("chart", {"chart_name": SALES_TREND_CHART_LABEL, "col": 12}))

    doc = frappe.new_doc("Workspace")
    doc.label = CEO_WORKSPACE_LABEL
    doc.title = CEO_WORKSPACE_LABEL
    doc.category = "Modules"
    doc.is_hidden = 0
    doc.public = 1
    doc.module = "Azeon Core"
    doc.icon = "dashboard"
    doc.content = frappe.as_json(content)
    # Restrict visibility to the System Manager role, per Phase 3 spec.
    doc.append("roles", {"role": "System Manager"})
    doc.insert(ignore_permissions=True)
