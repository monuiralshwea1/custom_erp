# Copyright (c) 2026, moneer
# License: MIT
"""إعدادات نظام مراقبة نشاط المستخدمين (User Activity Audit & Monitoring)."""

import frappe

SETTINGS_DOCTYPE = "User Activity Audit Settings"
LOG_DOCTYPE = "User Activity Audit Log"
AUDIT_ROLE = "Audit Manager"

# مستندات نظام لا يجوز تسجيلها (منع الحلقات المتكررة وNoise)
SKIP_DOCTYPES = {
	LOG_DOCTYPE,
	SETTINGS_DOCTYPE,
	"Version",
	"Activity Log",
	"Access Log",
	"Route History",
	"View Log",
	"Error Log",
	"Notification Log",
	"Scheduled Job Log",
	"__Global Search",
	"Personal Details",
	"User",
	"Session Default",
	"DocType",
	"Report",
	"Workspace",
}

DEFAULT_SENSITIVE_PATTERNS = (
	"password, passwd, pwd, secret, token, api_key, api_secret, "
	"private_key, signature, otp, credential"
)

# الحقول التي نقرأها من سجل الإعدادات
_SETTING_FIELDS = (
	"enabled",
	"retention_days",
	"max_rows_per_page",
	"capture_document_events",
	"capture_login_events",
	"capture_request_events",
	"capture_route_visits",
	"include_native_route_history",
	"include_native_access_log",
	"include_native_view_log",
	"include_native_version",
	"route_dedupe_seconds",
	"sensitive_field_patterns",
)


def _default_settings():
	"""قيم افتراضية آمنة إذا لم يكن سجل الإعدادات مُهيّأ."""
	values = frappe._dict(
		{
			"enabled": 1,
			"retention_days": 90,
			"max_rows_per_page": 100,
			"capture_document_events": 1,
			"capture_login_events": 1,
			"capture_request_events": 1,
			"capture_route_visits": 1,
			"include_native_route_history": 1,
			"include_native_access_log": 1,
			"include_native_view_log": 1,
			"include_native_version": 0,
			"route_dedupe_seconds": 60,
			"sensitive_field_patterns": DEFAULT_SENSITIVE_PATTERNS,
		}
	)
	values["excluded_doctypes"] = []
	values["excluded_fields"] = []
	return values


def _read_singles():
	"""قراءة قيم الإعدادات مباشرة من `tabSingles` (قراءة سريعة وخفيفة)."""
	rows = frappe.db.sql(
		"select `field`, `value` from `tabSingles` where `doctype` = %s",
		(SETTINGS_DOCTYPE,),
	)
	return {r[0]: r[1] for r in rows}


def get_settings():
	"""إرجاع إعدادات التدقيق.

	تُقرأ القيم مباشرة من قاعدة البيانات (بدون ذاكرة تخزين مؤقتة) لضمان
	أن التغييرات التي يجريها المستخدم تُقرأ فوراً، مع تخزين مؤقت قصير
	داخل الطلب الواحد لتفادي تكرار الاستعلام.
	"""
	cached = getattr(frappe.local, "_audit_settings_cache", None)
	if cached is not None:
		return cached

	settings = _default_settings()

	try:
		raw = _read_singles()
	except Exception:
		raw = {}

	for field in _SETTING_FIELDS:
		if field in raw and raw[field] is not None:
			settings[field] = raw[field]

	# تحويل الأنواع
	settings["enabled"] = cint_bool(settings.get("enabled"))
	for field in (
		"retention_days",
		"max_rows_per_page",
		"route_dedupe_seconds",
		"capture_document_events",
		"capture_login_events",
		"capture_request_events",
		"capture_route_visits",
		"include_native_route_history",
		"include_native_access_log",
		"include_native_view_log",
		"include_native_version",
	):
		settings[field] = cint_bool(settings.get(field))

	# الجداول الفرعية (الاستثناءات) - قراءة مباشرة لتجاوز قيود الصلاحيات
	# (هذه بيانات إعداد داخلية لا تُعرض للمستخدمين)
	settings["excluded_doctypes"] = [
		{"name": r[0], "excluded_doctype": r[1], "reason": r[2]}
		for r in frappe.db.sql(
			"""
			select `name`, `excluded_doctype`, `reason`
			from `tabAudit Excluded DocType`
			where `parent` = %s and `parenttype` = %s
			order by `idx` asc
			""",
			(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE),
		)
	]
	settings["excluded_fields"] = [
		{"name": r[0], "excluded_doctype": r[1], "excluded_fieldname": r[2], "reason": r[3]}
		for r in frappe.db.sql(
			"""
			select `name`, `excluded_doctype`, `excluded_fieldname`, `reason`
			from `tabAudit Excluded Field`
			where `parent` = %s and `parenttype` = %s
			order by `idx` asc
			""",
			(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE),
		)
	]

	frappe.local._audit_settings_cache = settings
	return settings


def cint_bool(value):
	"""تحويل قيمة إلى int (0/1)."""
	try:
		return int(value or 0)
	except (TypeError, ValueError):
		return 0


def clear_settings_cache():
	"""إلغاء ذاكرة التخزين المؤقتة لإعدادات التدقيق."""
	try:
		frappe.local._audit_settings_cache = None
	except Exception:
		pass
	try:
		frappe.clear_document_cache(SETTINGS_DOCTYPE)
	except Exception:
		pass


def is_enabled():
	try:
		return bool(get_settings().get("enabled"))
	except Exception:
		return False


def capture_enabled(kind):
	"""kind: document | login | request"""
	if not is_enabled():
		return False
	settings = get_settings()
	flags = {
		"document": settings.get("capture_document_events"),
		"login": settings.get("capture_login_events"),
		"request": settings.get("capture_request_events"),
	}
	return bool(flags.get(kind, True))


def should_skip_doctype(doctype):
	if not doctype:
		return True
	if doctype in SKIP_DOCTYPES:
		return True
	settings = get_settings()
	for row in settings.get("excluded_doctypes") or []:
		if row.get("excluded_doctype") == doctype:
			return True
	return False


def get_excluded_fields(doctype):
	"""قائمة الحقول المستثناة لنوع مستند معيّن."""
	excluded = set()
	settings = get_settings()
	for row in settings.get("excluded_fields") or []:
		if row.get("excluded_doctype") == doctype:
			excluded.add(row.get("excluded_fieldname"))
	return excluded


def get_sensitive_patterns():
	settings = get_settings()
	raw = settings.get("sensitive_field_patterns") or DEFAULT_SENSITIVE_PATTERNS
	patterns = [p.strip().lower() for p in str(raw).replace("\n", ",").split(",") if p.strip()]
	return patterns


def is_sensitive_field(doctype, fieldname):
	"""هل الحقل حسّاس (لا يُسجَّل حتى اسمُه)؟"""
	if not fieldname:
		return False

	if fieldname in get_excluded_fields(doctype):
		return True

	name = fieldname.lower()
	for pattern in get_sensitive_patterns():
		if pattern and pattern in name:
			return True
	return False


def get_route_dedupe_seconds():
	try:
		return int(get_settings().get("route_dedupe_seconds") or 0)
	except Exception:
		return 60


def get_max_rows_per_page():
	try:
		return max(1, int(get_settings().get("max_rows_per_page") or 100))
	except Exception:
		return 100


def get_retention_days():
	try:
		return int(get_settings().get("retention_days") or 0)
	except Exception:
		return 0


def native_source_enabled(flag):
	try:
		return bool(get_settings().get(flag))
	except Exception:
		return False
