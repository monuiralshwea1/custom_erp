frappe.ui.form.on('*', {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button('جديد', function() {
                frappe.new_doc(frm.doctype);
            }).addClass('btn-success'); // لون أخضر
        }
    }
});