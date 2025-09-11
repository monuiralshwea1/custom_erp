import frappe

def add_new_button(doc, method=None):
    # فقط للشاشات القابلة لإنشاء مستند جديد
    if doc.get("doctype") and doc.docstatus < 2:
        frappe.db.commit()  # تأكد أن السيشن جاهز

        # إضافة الزر عبر JS
        frappe.msgprint("""
            <script>
                frappe.ui.form.on("{}", {{
                    refresh: function(frm) {{
                        if (!frm.is_new()) {{
                            frm.add_custom_button("جديد", function() {{
                                frappe.new_doc("{}");
                            }}).addClass('btn-primary');
                        }}
                    }}
                }});
            </script>
        """.format(doc.doctype, doc.doctype))
