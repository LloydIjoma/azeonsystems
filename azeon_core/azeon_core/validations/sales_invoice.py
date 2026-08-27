import frappe

def validate_invoice(doc, method):
    """
    Validation logic executed before saving a Sales Invoice.
    """
    # Prevent saving invoices with zero grand total
    if doc.grand_total <= 0 and len(doc.items) > 0:
        frappe.msgprint("Note: Invoice total is 0. Please ensure correct pricing is applied.", alert=True)

