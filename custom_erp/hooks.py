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

persistent_cache_keys = ["session"]

doc_events = {
    "*": {
        "refresh": "custom_erp.custom_erp.api.add_new_button.add_new_button",
        "before_insert": "custom_erp.company_isolation.apply_default_company",
        "validate": "custom_erp.company_isolation.validate_company_access",
        "before_naming": "custom_erp.company_sequence.apply_company_prefix",
        # --- User Activity Audit & Monitoring ---
        "after_insert": "custom_erp.custom_app.audit.document_events.handle_after_insert",
        "on_update": "custom_erp.custom_app.audit.document_events.handle_on_update",
        "on_submit": "custom_erp.custom_app.audit.document_events.handle_on_submit",
        "on_cancel": "custom_erp.custom_app.audit.document_events.handle_on_cancel",
        "on_trash": "custom_erp.custom_app.audit.document_events.handle_on_trash",
    },
    "Company": {
        "after_insert": "custom_erp.company_isolation.grant_company_to_creator",
    },
    "User": {
        "validate": "custom_erp.company_isolation.validate_company_access",
        "on_update": "custom_erp.company_isolation.sync_user_company_permission",
    },
}

# --- User Activity Audit & Monitoring ---
# سجل التدقيق يجب ألا يمنع حذف المستند المُوثَّق (مثل Activity Log و Version في Frappe)
ignore_links_on_delete = [
    "User Activity Audit Log",
]

# إنشاء دور المراجع وضبط الإعدادات الافتراضية بعد الترحيل
after_migrate = [
    "custom_erp.custom_app.audit.setup.setup",
]

# تنظيف سجلات التدقيق القديمة وفق سياسة الاحتفاظ (يومياً)
scheduler_events = {
    "daily": [
        "custom_erp.custom_app.audit.tasks.purge_expired_audit_logs",
    ],
}

# التقاط أحداث الطلبات (طباعة / تصدير / تنزيل / أخطاء / صلاحيات مرفوضة)
after_request = [
    "custom_erp.custom_app.audit.request_events.after_request",
]

# التقاط تسجيل الدخول والخروج (تتم إضافة هذه الدوال إلى Hooks الأصلية في Frappe
# ولا تستبدلها، لأن Frappe يدمج قوائم الـHooks بين التطبيقات)
on_login = [
    "custom_erp.custom_app.audit.auth_events.on_login",
]

on_logout = [
    "custom_erp.custom_app.audit.auth_events.on_logout",
]

on_session_creation = [
    "custom_erp.custom_app.audit.auth_events.on_session_creation",
]

permission_query_conditions = {
    "*": "custom_erp.company_isolation.get_permission_query_conditions",
}

has_permission = {
    "*": "custom_erp.company_isolation.has_permission",
}

app_include_js = [
    "/assets/custom_erp/js/add_new_button.js",
    "/assets/custom_erp/js/global_button.js",
    "/assets/custom_erp/js/navigation_buttons_force.js",
    "/assets/custom_erp/js/desk_tabs.js",
    "/assets/custom_erp/js/dev_gate.js"
]

app_include_css = [
    "/assets/custom_erp/css/navigation_buttons.css",
    "/assets/custom_erp/css/desk_tabs.css"
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

# ============================================================================
# Central Module Control Manager
# نظام مركزي لإدارة وإخفاء وتعطيل الموديولات (Central Module Control Manager)
# الذي يضيف هذا الملف: يُدمج مع الـHooks الموجود أعلاه دون استبداله.
# ============================================================================
doc_events.update(
	{
		"Module Def": {
			"after_insert": "custom_erp.custom_app.module_control.sync.on_module_changed",
			"on_update": "custom_erp.custom_app.module_control.sync.on_module_changed",
		},
		"Workspace": {
			"after_insert": "custom_erp.custom_app.module_control.sync.on_workspace_changed",
			"on_update": "custom_erp.custom_app.module_control.sync.on_workspace_changed",
		},
		# Role Guard — منع إسناد أدوار محميّة (مثل Workspace Manager) لأي مستخدم
		"User": {
			"validate": [
				"custom_erp.company_isolation.validate_company_access",
				"custom_erp.custom_app.module_control.role_guard.validate_user_role_assignment",
			],
			"on_update": "custom_erp.company_isolation.sync_user_company_permission",
		},
		"Role Profile": {
			"validate": "custom_erp.custom_app.module_control.role_guard.validate_role_profile_assignment",
		},
		"Role": {
			"before_validate": "custom_erp.custom_app.module_control.role_guard.enforce_protected_role_disabled",
		},
	}
)

after_install = [
	"custom_erp.custom_app.module_control.sync.setup_after_install",
]

after_migrate += [
	"custom_erp.custom_app.module_control.sync.after_migrate",
]

before_request = [
	"custom_erp.custom_app.module_control.permissions.before_request_hook",
]

boot_session = [
	"custom_erp.custom_app.module_control.workspace_filter.boot_session_hook",
]

# NOTE: has_permission here is DOC-LEVEL (controller). Access blocking for
# Administrator is bypassed by Frappe core itself (documented limitation).
has_permission.update(
	{
		"*": "custom_erp.custom_app.module_control.permissions.has_permission_hook",
	}
)

permission_query_conditions.update(
	{
		"*": "custom_erp.custom_app.module_control.permissions.query_conditions_hook",
	}
)

# HTTP-level overrides (official hook). The Python-internal call sites
# (boot.load_desktop_data, frappe.apps.get_apps) are additionally covered by
# the documented module-attribute patch installed at import time below.
override_whitelisted_methods = {
	"frappe.desk.desktop.get_workspace_sidebar_items":
		"custom_erp.custom_app.module_control.workspace_filter.get_workspace_sidebar_items_filtered",
	"frappe.desk.desktop.get_desktop_page":
		"custom_erp.custom_app.module_control.workspace_filter.get_desktop_page_filtered",
}

app_include_js += [
	"/assets/custom_erp/js/module_control_settings.js",
]

app_include_css += [
	"/assets/custom_erp/css/module_control.css",
]

# Install the (documented, minimal, idempotent) desktop visibility wrappers.
try:
	from custom_erp.custom_app.module_control.workspace_filter import ensure_desktop_patched as _mc_ensure_patch

	_mc_ensure_patch()
except Exception:
	import traceback
	try:
		import frappe as _frappe
		_frappe.log_error(traceback.format_exc()[:2000], "ModuleControl patch init")
	except Exception:
		pass
