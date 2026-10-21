# Copyright (c) 2026, moneer
# License: MIT
"""واجهات برمجية نظام مراقبة نشاط المستخدمين (محمية بصلاحيات القراءة)."""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, now_datetime

from custom_erp.custom_app.audit import config, query as audit_query

LOG_DOCTYPE = "User Activity Audit Log"
SETTINGS_DOCTYPE = "User Activity Audit Settings"


def _check_permission():
	if not frappe.has_permission(LOG_DOCTYPE, "read"):
		frappe.throw(_("Not permitted to read activity audit records."), frappe.PermissionError)


@frappe.whitelist()
def get_audit_summary(days=30):
	"""ملخص إداري سريع لمؤشرات النشاط.

	المؤشرات إحصاءات نشاط، وليست دليلاً على إساءة الاستخدام.
	"""
	_check_permission()

	days = max(1, min(int(days or 30), 365))
	to_date = getdate(now_datetime())
	from_date = add_days(to_date, -days)

	filters = {"from_date": from_date, "to_date": to_date}

	rows = audit_query.fetch_events(filters, start=0, page_length=10000)

	by_type = {}
	by_user = {}
	by_document = {}
	by_outcome = {}

	for row in rows:
		by_type[row.get("activity_type") or "Other"] = (
			by_type.get(row.get("activity_type") or "Other", 0) + 1
		)
		if row.get("user"):
			by_user[row["user"]] = by_user.get(row["user"], 0) + 1
		if row.get("reference_name"):
			key = f"{row.get('reference_doctype') or ''}:{row['reference_name']}"
			by_document[key] = by_document.get(key, 0) + 1
		if row.get("outcome"):
			by_outcome[row["outcome"]] = by_outcome.get(row["outcome"], 0) + 1

	top_users = sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:10]
	top_documents = sorted(by_document.items(), key=lambda x: x[1], reverse=True)[:10]

	unusual = []
	failed = by_type.get("Failed Login", 0)
	denied = by_type.get("Access Denied", 0)
	errors = by_type.get("Error", 0)

	if failed:
		unusual.append(
			_("{0} failed login attempt(s) recorded - review authentication logs.").format(failed)
		)
	if denied:
		unusual.append(
			_("{0} request(s) rejected by permissions - verify role assignments.").format(denied)
		)
	if errors:
		unusual.append(_("{0} server error(s) recorded during the period.").format(errors))

	off_hours = 0
	for row in rows:
		try:
			hour = (row.get("activity_datetime") or now_datetime()).hour
		except Exception:
			continue
		if hour >= 0 and hour < 6:
			off_hours += 1
	if off_hours:
		unusual.append(
			_("{0} event(s) were recorded between midnight and 6 AM.").format(off_hours)
		)

	return {
		"period_days": days,
		"from_date": from_date,
		"to_date": to_date,
		"total_events": len(rows),
		"active_users": len(by_user),
		"by_type": by_type,
		"by_outcome": by_outcome,
		"top_users": [{"user": u, "events": c} for u, c in top_users],
		"top_documents": [{"document": d, "events": c} for d, c in top_documents],
		"unusual_events": unusual,
		"note": _(
			"These are activity indicators only. They are not evidence of misconduct and "
			"must be reviewed together with the surrounding context before any conclusion."
		),
	}


@frappe.whitelist()
def get_audit_settings():
	"""قراءة إعدادات التدقيق (للمستخدم المخوّل فقط)."""
	if not frappe.has_permission(SETTINGS_DOCTYPE, "read"):
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
	return {
		"enabled": settings.enabled,
		"retention_days": settings.retention_days,
		"max_rows_per_page": settings.max_rows_per_page,
		"capture_document_events": settings.capture_document_events,
		"capture_login_events": settings.capture_login_events,
		"capture_request_events": settings.capture_request_events,
		"capture_route_visits": settings.capture_route_visits,
		"include_native_route_history": settings.include_native_route_history,
		"include_native_access_log": settings.include_native_access_log,
		"include_native_view_log": settings.include_native_view_log,
		"include_native_version": settings.include_native_version,
		"route_dedupe_seconds": settings.route_dedupe_seconds,
		"sensitive_field_patterns": settings.sensitive_field_patterns,
	}


@frappe.whitelist()
def purge_old_audit_logs(days=None):
	"""حذف السجلات الأقدم من مدة الاحتفاظ (يدوي أو من جدولة يومية)."""
	if not ("System Manager" in frappe.get_roles() or "Audit Manager" in frappe.get_roles()):
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	retention = cint(days) if days else config.get_retention_days()
	if not retention:
		return {"deleted": 0, "message": _("Retention is not set - nothing was deleted.")}

	cutoff = add_days(getdate(now_datetime()), -int(retention))
	deleted = frappe.db.sql(
		"DELETE FROM `tabUser Activity Audit Log` WHERE `creation` < %s",
		(str(cutoff),),
	)
	frappe.db.commit()

	return {"deleted": deleted, "cutoff": cutoff}
