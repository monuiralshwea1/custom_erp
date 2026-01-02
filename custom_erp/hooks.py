app_name = "custom_erp"
app_title = "custom app"
app_publisher = "moneer"
app_description = "new testine app"
app_email = "M777682260@gmail.com"
app_license = "mit"

fixtures = [
    {
        "dt": "Client Script",
        "filters": [
            ["name", "in", [
                "Back Button in Header",
                "زر اضافة فاتورة نقدية",
                "sales valu",
                "اضافة زر جديد",
                "clear profile",
                "Client script pos",
                "زر مرتجع ونقد في الفاتورة",
                "form cash purchase invoice",
                "cash purchase invoice",
                "enable tax",
                "اضافة فاتورة نقدية",
                "مرتجع مع نقد",
                "اضافة زر تعديل الفاتورة المعتمدة",
                "تعديل الفاتورة بعد الاعتماد",
                "test",
                "test2",
                "POS Invoice",
                "pos2",
                "add buton asset form",
                "add buton asset list",
                "اضافة زر اضافة جديد للواجهات"
            ]]
        ]
    },
    "Custom Field",
    "Property Setter",
    "Print Format",
    "Report",
    "Workflow",
    "Workflow State",
    "Workflow Action",
    "Workspace",
    "Translation"
]

doc_events = {
    "*": {
        "refresh": "custom_erp.custom_erp.api.add_new_button.add_new_button"
    }
}

app_include_js = [
    "/assets/custom_erp/js/add_new_button.js",
    "/assets/custom_erp/js/global_button.js",
    "/assets/custom_erp/js/navigation_buttons_force.js"
]

app_include_css = [
    "/assets/custom_erp/css/navigation_buttons.css"
]

# required_apps = []

# Includes in <head>
# ------------------

# app_include_css = "/assets/custom_erp/css/custom_erp.css"
# app_include_js = "/assets/custom_erp/js/custom_erp.js"

# web_include_css = "/assets/custom_erp/css/custom_erp.css"
# web_include_js = "/assets/custom_erp/js/custom_erp.js"

# website_theme_scss = "custom_erp/public/scss/website"

# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# page_js = {"page" : "public/js/file.js"}

# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# app_include_icons = "custom_erp/public/icons.svg"

# home_page = "login"

# role_home_page = {
# 	"Role": "home_page"
# }

# website_generators = ["Web Page"]

# jinja = {
# 	"methods": "custom_erp.utils.jinja_methods",
# 	"filters": "custom_erp.utils.jinja_filters"
# }

# before_install = "custom_erp.install.before_install"
# after_install = "custom_erp.install.after_install"

# before_uninstall = "custom_erp.uninstall.before_uninstall"
# after_uninstall = "custom_erp.uninstall.after_uninstall"

# before_app_install = "custom_erp.utils.before_app_install"
# after_app_install = "custom_erp.utils.after_app_install"

# before_app_uninstall = "custom_erp.utils.before_app_uninstall"
# after_app_uninstall = "custom_erp.utils.after_app_uninstall"

# notification_config = "custom_erp.notifications.get_notification_config"

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }

# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# scheduler_events = {
# 	"all": [
# 		"custom_erp.tasks.all"
# 	],
# 	"daily": [
# 		"custom_erp.tasks.daily"
# 	],
# 	"hourly": [
# 		"custom_erp.tasks.hourly"
# 	],
# 	"weekly": [
# 		"custom_erp.tasks.weekly"
# 	],
# 	"monthly": [
# 		"custom_erp.tasks.monthly"
# 	],
# }

# before_tests = "custom_erp.install.before_tests"

# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "custom_erp.event.get_events"
# }

# override_doctype_dashboards = {
# 	"Task": "custom_erp.task.get_dashboard_data"
# }

# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# ignore_links_on_delete = ["Communication", "ToDo"]

# before_request = ["custom_erp.utils.before_request"]
# after_request = ["custom_erp.utils.after_request"]

# before_job = ["custom_erp.utils.before_job"]
# after_job = ["custom_erp.utils.after_job"]

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# auth_hooks = [
# 	"custom_erp.auth.validate"
# ]

# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30
# }
