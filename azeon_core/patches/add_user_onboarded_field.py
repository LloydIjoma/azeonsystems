"""
Backfill for tenants provisioned before the "onboarded" Custom Field on
User existed (see azeon_core.subscription_gate.create_onboarded_field —
now also run at install time via setup_dashboard.after_install).

Without this field, azeon_core.subscription_gate.complete_onboarding()
(called from the onboarding wizard's "Complete Onboarding" button, after
the company logo step) crashes on:
    pymysql.err.OperationalError: (1054, "Unknown column 'onboarded' in 'SET'")
because User.db_set("onboarded", 1) issues a raw UPDATE against a column
that was never created.
"""

from azeon_core.subscription_gate import create_onboarded_field


def execute():
    create_onboarded_field()
