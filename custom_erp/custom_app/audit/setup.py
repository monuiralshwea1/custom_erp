# Copyright (c) 2026, moneer
# License: MIT
"""تهيئة نظام مراقبة نشاط المستخدمين: إنشاء دور المراجع وربط الصلاحيات."""

import frappe

AUDIT_ROLE = "Audit Manager"
AUDIT_LOG_DOCTYPE = "User Activity Audit Log"
SETTINGS_DOCTYPE = "User Activity Audit Settings"


def ensure_audit_role():
	"""إنشاء دور `Audit Manager` إن لم يكن موجوداً."""
	if frappe.db.exists("Role", AUDIT_ROLE):
		return

	role = frappe.get_doc(
		{
			"doctype": "Role",
			"role_name": AUDIT_ROLE,
			"desk_access": 1,
			"is_custom": 1,
			"disabled": 0,
		}
	)
	role.insert(ignore_permissions=True, ignore_if_duplicate=True)
	frappe.db.commit()


def ensure_settings_defaults():
	"""إنشاء سجل الإعدادات الافتراضي عند أول تشغيل."""
	if not frappe.db.exists("DocType", SETTINGS_DOCTYPE):
		return

	if frappe.db.exists("Singles", {"doctype": SETTINGS_DOCTYPE}):
		return

	settings = frappe.get_single(SETTINGS_DOCTYPE)
	settings.enabled = 1
	settings.retention_days = 90
	settings.max_rows_per_page = 100
	settings.route_dedupe_seconds = 60
	settings.capture_document_events = 1
	settings.capture_login_events = 1
	settings.capture_request_events = 1
	settings.capture_route_visits = 1
	settings.include_native_route_history = 1
	settings.include_native_access_log = 1
	settings.include_native_view_log = 1
	settings.include_native_version = 0
	settings.flags.ignore_permissions = True
	settings.save(ignore_permissions=True)
	frappe.db.commit()


def setup():
	"""نقطة الدخول من after_migrate."""
	ensure_audit_role()
	ensure_settings_defaults()
