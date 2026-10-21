# Copyright (c) 2026, moneer
# License: MIT
"""طبقة التسجيل الموحّدة لنشاط المستخدمين.

كل الأحداث تُسجَّل من الخادم فقط:
- المستخدم يُؤخذ من الجلسة الموثّقة (frappe.session.user).
- عنوان IP من frappe.local.request_ip.
- لا تُسجَّل أي قيم للحقول، بل أسماء الحقول المتغيّرة فقط.
"""

import frappe
from frappe.utils import now

from custom_erp.custom_app.audit import config


def get_request_ip():
	try:
		return frappe.local.request_ip
	except Exception:
		return None


def get_user_agent():
	try:
		return (frappe.request.headers.get("User-Agent") or "")[:255]
	except Exception:
		return None


def get_correlation_id():
	"""معرّف ارتباط للطلب الحالي."""
	try:
		rid = frappe.request.headers.get("X-Frappe-Request-Id")
		if rid:
			return rid
	except Exception:
		pass
	return frappe.generate_hash(length=12)


def get_session_user():
	try:
		return frappe.session.user
	except Exception:
		return "Guest"


def is_suppressed():
	"""حالات لا يُسجَّل فيها أي نشاط (ترحيل، تثبيت، اختبارات.batch)."""
	flags = frappe.flags
	return bool(
		flags.in_install
		or flags.in_migrate
		or flags.in_patch
		or flags.in_import
		or flags.in_setup_wizard
	)


def log_activity(
	activity_type,
	outcome="Success",
	user=None,
	reference_doctype=None,
	reference_name=None,
	page_route=None,
	changed_fields=None,
	details=None,
	source="Custom App",
	ip_address=None,
	user_agent=None,
	http_method=None,
	api_method=None,
	correlation_id=None,
	attempted_user=None,
	activity_datetime=None,
):
	"""تسجيل حدث نشاط واحد.

	يُرجع اسم السجل المُنشأ أو None إذا كان التسجيل معطّلاً/مُتجاهلاً.
	"""
	if is_suppressed():
		return None

	if not config.is_enabled():
		return None

	# منع تسجيل سجل التدقيق نفسه
	if reference_doctype == config.LOG_DOCTYPE and activity_type not in ("Other",):
		return None

	session_user = get_session_user()
	if user is None:
		user = session_user

	# لا يُقبل مستخدم من المتصفح: إن كانSession != Guest فهو المرجع
	if session_user and session_user != "Guest":
		user = session_user

	if not user:
		user = "Guest"

	values = {
		"doctype": config.LOG_DOCTYPE,
		"naming_series": "UAL-.YYYY.-",
		"user": user,
		"activity_datetime": activity_datetime or now(),
		"activity_type": activity_type,
		"outcome": outcome,
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
		"page_route": (page_route or None),
		"changed_fields": _normalise_fields(changed_fields),
		"details": (details or None),
		"source": source,
		"ip_address": ip_address or get_request_ip(),
		"user_agent": user_agent or get_user_agent(),
		"http_method": http_method,
		"api_method": api_method,
		"correlation_id": correlation_id or get_correlation_id(),
		"attempted_user": attempted_user,
	}

	values = {k: v for k, v in values.items() if v not in (None, "")}

	try:
		doc = frappe.get_doc(values)
		doc.insert(ignore_permissions=True, ignore_links=True, ignore_mandatory=True)
		return doc.name
	except Exception:
		# لا نُفشل العملية الأصلية بسبب فشل التسجيل
		frappe.log_error(
			title="User Activity Audit: failed to log activity",
			message=frappe.get_traceback(),
		)
		return None


def _normalise_fields(changed_fields):
	"""تحويل أسماء الحقول إلى نص مختصر (أسماء فقط، بلا قيم)."""
	if not changed_fields:
		return None
	if isinstance(changed_fields, str):
		parts = [p.strip() for p in changed_fields.split(",")]
	else:
		parts = [str(p).strip() for p in changed_fields]
	parts = [p for p in parts if p]
	if not parts:
		return None
	return ", ".join(parts[:50])


def should_dedupe(key, window_seconds):
	"""منع تكرار التسجيل المتكرر لنفس الحدث خلال نافذة زمنية."""
	if not window_seconds or not key:
		return False
	cache_key = f"audit_dedupe:{key}"
	try:
		if frappe.cache().get_value(cache_key, expires=True):
			return True
		frappe.cache().set_value(cache_key, 1, expires_in_sec=window_seconds)
	except Exception:
		return False
	return False
