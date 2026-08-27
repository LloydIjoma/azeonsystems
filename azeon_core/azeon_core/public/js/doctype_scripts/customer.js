frappe.ui.form.on('Customer', {
    refresh(frm) {
        // Add a custom quick button on Customer form
        if (!frm.is_new()) {
            frm.add_custom_button(__('Create Azeon Order'), function() {
                frappe.route_options = {
                    "customer": frm.doc.name
                };
                frappe.new_doc('Sales Order');
            }, __('Actions'));
        }
    }
});
