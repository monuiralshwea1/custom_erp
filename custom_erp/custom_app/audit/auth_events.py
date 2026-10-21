# Copyright (c) 2026, moneer
# License: MIT
"""التقاط أحداث المصادقة: تسجيل دخول، خروج، ومحاولات دخول فاشلة."""

import frappe

from custom_erp.custom_app.audit import config, logger


def on_login(login_manager=None):
	"""يُستدعى عند تسجيل الدخول بنجاح.

	المستخدم يُؤخذ من الجلسة الموثّقة، ولا يُقبل من المتصفح.
	"""
	if not config.capture_enabled("login"):
		return

	user = frappe.session.user
	if not user or user == "Guest":
		return

	logger.log_activity(
		"Login",
		outcome="Success",
		user=user,
		details=frappe._("User {0} logged in").format(user),
	)


def on_session_creation(login_manager=None):
	"""يُستدعى عند إنشاء جلسة جديدة (تسجيل دخول فعلي).

	`on_login` و`on_session_creation` يُطلقان معاً في Frappe،
	لذلك نستخدم `on_session_creation` للتسجيل الفعلي ونترك `on_login` بلا أثر مكرر.
	"""
	return


def on_logout(login_manager=None):
	"""يُستدعى عند تسجيل الخروج."""
	if not config.capture_enabled("login"):
		return

	user = frappe.session.user
	if not user or user == "Guest":
		return

	logger.log_activity(
		"Logout",
		outcome="Success",
		user=user,
		details=frappe._("User {0} logged out").format(user),
	)


def log_failed_login(attempted_user, reason=None, ip_address=None):
	"""تسجيل محاولة دخول فاشلة.

	ملاحظة: اسم المستخدم هنا هو المُدخل في الطلب وليس هوية موثّقة،
	لذلك يُسجَّل في حقل attempted_user ويبقى user = Guest.
	"""
	if not config.capture_enabled("login"):
		return

	logger.log_activity(
		"Failed Login",
		outcome="Failure",
		user="Guest",
		attempted_user=(attempted_user or "")[:140],
		ip_address=ip_address,
		details=reason or frappe._("Failed login attempt"),
	)
