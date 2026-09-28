import frappe

def create_invoice_notification():
    notification_name = "Azeon Invoice Submitted Notification"
    
    if not frappe.db.exists("Notification", notification_name):
        doc = frappe.new_doc("Notification")
        doc.name = notification_name
        doc.subject = "Sales Invoice {{ doc.name }} from {{ doc.company }}"
        doc.document_type = "Sales Invoice"
        doc.event = "Submit"
        doc.channel = "Email"
        doc.send_to_all_assignees = 0
        doc.attach_print = 1
        doc.print_format = "Azeon Invoice"
        
        # Recipients configuration
        doc.append("recipients", {
            "recipients": "customer_address"  # Sends to primary customer email
        })
        
        # Email Body Template
        doc.message = """
<div style="font-family: Arial, sans-serif; color: #334155;">
    <h3>Hello {{ doc.customer_name }},</h3>
    <p>Thank you for your business. Please find attached your Sales Invoice <strong>{{ doc.name }}</strong> for the amount of <strong>{{ doc.get_formatted("grand_total") }}</strong>.</p>
    <p>If you have any questions regarding this invoice, please reach out to our support team.</p>
    <br>
    <p>Best regards,<br><strong>{{ doc.company }}</strong></p>
</div>
"""
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Sales Invoice notification rule created successfully.")
    else:
        print("Notification rule already exists.")

