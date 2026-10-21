# Copyright (c) 2026, moneer
# License: MIT
"""التقاط أحداث الطلبات على الخادم: طباعة، تصدير، تنزيل، محاولات دخول فاشلة،
صلاحيات مرفوضة، أخطاء، وزيارات الواجهات (عبر Referer مع منع التكرار)."""

import frappe
from urllib.parse import urlparse

from custom_erp.custom_app.audit import auth_events, config, logger

# مسارات تداخل تسجيل الدخول
LOGIN_PATHS = (
	"/api/method/login",
	"/api/method/frappe.auth.login",
	"/login",
)

PRINT_PATTERNS = (
	"download_pdf",
	"/printview",
)

EXPORT_PATTERNS = (
	"export_query",
	"export_data",
)

DOWNLOAD_PATTERNS = (
	"download_file",
	"/private/files/",
	"frappe.utils.file.download",
)


def get_path(request):
	try:
		return (request.path or "").lower()
	except Exception:
		return ""


def get_referer_route(request):
	"""مسار الصفحة التي أُرسل منها الطلب (من ترويسة Referer)."""
	try:
		referer = request.headers.get("Referer")
		if not referer:
			return None
		path = urlparse(referer).path
		return path or None
	except Exception:
		return None


def get_api_method(request):
	try:
		path = request.path or ""
		if "/api/method/" in path:
			return path.split("/api/method/", 1)[1].split("?")[0]
	except Exception:
		pass
	return None


def get_form_value(request, key):
	try:
		value = request.form.get(key)
		if value:
			return value
	except Exception:
		pass
	try:
		return frappe.local.form_dict.get(key)
	except Exception:
		return None


def after_request(request, response):
	"""يُنفَّذ بعد كل طلب ويجمع الأحداث الموثوقة من الخادم."""
	try:
		_logged = False

		path = get_path(request)
		status = getattr(response, "status_code", 0)

		# 1) محاولة دخول فاشلة
		if path in LOGIN_PATHS and status in (401, 403):
			attempted_user = get_form_value(request, "usr") or get_form_value(request, "user")
			auth_events.log_failed_login(
				attempted_user,
				reason=frappe._("Invalid credentials"),
				ip_address=logger.get_request_ip(),
			)
			_logged = True

		# 2) طباعة مستند (PDF) أو معاينته
		elif any(pattern in path for pattern in PRINT_PATTERNS):
			doctype = get_form_value(request, "doctype")
			name = get_form_value(request, "name")
			logger.log_activity(
				"Document Print",
				outcome="Success",
				reference_doctype=doctype,
				reference_name=name,
				page_route=get_referer_route(request),
				details=frappe._("Printed / downloaded as PDF"),
				http_method=request.method,
				api_method=get_api_method(request),
			)
			_logged = True

		# 3) تصدير تقارير / بيانات
		elif any(pattern in path for pattern in EXPORT_PATTERNS):
			logger.log_activity(
				"Report Export",
				outcome="Success",
				page_route=get_referer_route(request),
				details=frappe._("Exported report data"),
				http_method=request.method,
				api_method=get_api_method(request),
			)
			_logged = True

		# 4) تنزيل ملفات
		elif any(pattern in path for pattern in DOWNLOAD_PATTERNS):
			logger.log_activity(
				"File Download",
				outcome="Success",
				page_route=get_referer_route(request),
				details=frappe._("Downloaded a file"),
				http_method=request.method,
				api_method=get_api_method(request),
			)
			_logged = True

		# 5) رفض صلاحية
		if status == 403 and path.startswith("/api/"):
			logger.log_activity(
				"Access Denied",
				outcome="Denied",
				page_route=get_referer_route(request),
				details=frappe._("Request rejected by permissions"),
				http_method=request.method,
				api_method=get_api_method(request),
			)
			_logged = True

		# 6) خطأ في الخادم
		if status and status >= 500:
			logger.log_activity(
				"Error",
				outcome="Failure",
				page_route=get_referer_route(request),
				details=frappe._("Server error (HTTP {0})").format(status),
				http_method=request.method,
				api_method=get_api_method(request),
			)
			_logged = True

		# 7) زيارة واجهة (من Referer مع منع التكرار)
		if config.capture_enabled("request") and config.native_source_enabled("capture_route_visits"):
			_logged = _maybe_log_route_visit(request) or _logged

		if _logged:
			try:
				frappe.db.commit()
			except Exception:
				pass

	except Exception:
		# لا نُفشل الاستجابة بسبب المراقبة
		pass


def _maybe_log_route_visit(request):
	route = get_referer_route(request)
	if not route or not route.startswith("/app/"):
		return False

	user = frappe.session.user
	if not user or user == "Guest":
		return False

	window = config.get_route_dedupe_seconds()
	key = f"route:{user}:{route}"
	if logger.should_dedupe(key, window):
		return False

	return bool(
		logger.log_activity(
			"Route Visit",
			outcome="Success",
			user=user,
			page_route=route,
			details=frappe._("Visited {0}").format(route),
			http_method=request.method,
		)
	)
