frappe.provide("azeon.onboarding");

$(document).on("app_ready", function() {
    if (!frappe.boot.user.onboarded && frappe.session.user !== "Administrator") {
        azeon.onboarding.show_wizard();
    }
});

azeon.onboarding.show_wizard = function() {
    let d = new frappe.ui.Dialog({
        title: __('Welcome to Azeon Systems! 🚀'),
        fields: [
            {
                label: __('Company Name'),
                fieldname: 'company_name',
                fieldtype: 'Data',
                reqd: 1,
                default: frappe.boot.sysdefaults.company || ''
            },
            {
                label: __('Primary Industry'),
                fieldname: 'industry',
                fieldtype: 'Select',
                options: ['Services', 'Retail', 'Manufacturing', 'Technology', 'Other'],
                reqd: 1
            },
            {
                label: __('Company Logo'),
                fieldname: 'company_logo',
                fieldtype: 'Attach Image'
            }
        ],
        primary_action_label: __('Complete Onboarding'),
        primary_action(values) {
            frappe.call({
                method: 'azeon_core.subscription_gate.complete_onboarding',
                args: { data: values },
                callback: function(r) {
                    if (!r.exc) {
                        d.hide();
                        frappe.msgprint(__('Workspace ready! Let\'s get started.'));
                    }
                }
            });
        }
    });
    d.show();
};
