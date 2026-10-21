# Copyright (c) 2026, moneer
# License: MIT
"""استعلامات وتوحيد سجلات نشاط المستخدمين.

المصدر الأساسي: `User Activity Audit Log` (سجل موحّد داخل custom_erp).
المصادر الأصلية في Frappe: Route History / Activity Log / Access Log / View Log / Version.

قواعد التوحيد:
- كل الأحداث تُرجَع بنفس الشكل مع عمود `source` لتمييز المصدر.
- التكرار يُعالج على مستوى SQL: أي حدث أصلي (Frappe) يُسقَط إذا وُجد حدث
  مكافئ في السجل الموحّد (نفس المستخدم والنوع والمستند خلال 120 ثانية).
- الترتيب من الأحدث إلى الأقدم، والتقسيم إلى صفحات يتم على الخادم.
"""

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, now_datetime

from custom_erp.custom_app.audit import config

UNIFIED = "tabUser Activity Audit Log"

# نافذة اعتبار الحدثين نفسهما (بالثواني)
DEDUPE_WINDOW = 120

# خريطة أنواع Activity Log الأصلي -> نوع موحّد
ACTIVITY_LOG_TYPE_SQL = """
	CASE
		WHEN `operation` = 'Login' AND `status` = 'Failed' THEN 'Failed Login'
		WHEN `operation` = 'Login' THEN 'Login'
		WHEN `operation` = 'Logout' THEN 'Logout'
		WHEN `operation` = 'Impersonate' THEN 'Impersonate'
		ELSE `operation`
	END
"""

# خريطة أنواع Access Log الأصلي -> نوع موحّد
ACCESS_LOG_TYPE_SQL = """
	CASE
		WHEN `method` = 'Print' THEN 'Document Print'
		WHEN `method` = 'Export' THEN 'Report Export'
		ELSE CONCAT(IFNULL(`method`, ''), ' ', IFNULL(`file_type`, ''))
	END
"""


def _date_bounds(filters):
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	start = getdate(from_date) if from_date else getdate(now_datetime())
	end = getdate(to_date) if to_date else getdate(now_datetime())

	if start > end:
		start, end = end, start

	return f"{start} 00:00:00", f"{end} 23:59:59"


def _conditions(filters):
	"""الفلاتر الأساسية + الفلاتر الخاصة بكل مصدر."""
	start, end = _date_bounds(filters)
	conditions = {
		"from_datetime": start,
		"to_datetime": end,
		"user": filters.get("user") or "",
		"activity_type": filters.get("activity_type") or "",
		"reference_doctype": filters.get("reference_doctype") or "",
		"reference_name": filters.get("reference_name") or "",
		"page_route": filters.get("page_route") or "",
		"outcome": filters.get("outcome") or "",
		"ip_address": filters.get("ip_address") or "",
		"source": filters.get("source") or "",
	}
	return conditions


def _source_allowed(conditions, source):
	selected = conditions.get("source")
	if not selected:
		return True
	return selected == source


def _dedupe_clause(alias, type_expr, doctype_expr, name_expr, actor_expr=None):
	"""استبعاد الحدث الأصلي إذا وُجد مكافئ في السجل الموحّد.

	المطابقة تتم على: نوع النشاط + المستخدم الفعّال + المستند + زمن قريب.
	"""
	if actor_expr is None:
		actor_expr = f"COALESCE({alias}.`user`, '')"

	return f"""
		NOT EXISTS (
			SELECT 1 FROM `{UNIFIED}` u
			WHERE u.`creation` BETWEEN DATE_SUB({alias}.`creation`, INTERVAL {DEDUPE_WINDOW} SECOND)
			                        AND DATE_ADD({alias}.`creation`, INTERVAL {DEDUPE_WINDOW} SECOND)
			  AND u.`activity_type` = ({type_expr})
			  AND COALESCE(NULLIF(u.`attempted_user`, ''), u.`user`, '') = ({actor_expr})
			  AND COALESCE(u.`reference_doctype`, '') = COALESCE(({doctype_expr}), '')
			  AND COALESCE(u.`reference_name`, '') = COALESCE(({name_expr}), '')
		)
	"""


# --------------------------------------------------------------------- unified
def unified_query(conditions, limit=None, offset=0, for_count=False):
	where = ["`creation` BETWEEN %(from_datetime)s AND %(to_datetime)s"]
	if conditions.get("user"):
		where.append("`user` = %(user)s")
	if conditions.get("activity_type"):
		where.append("`activity_type` = %(activity_type)s")
	if conditions.get("reference_doctype"):
		where.append("`reference_doctype` = %(reference_doctype)s")
	if conditions.get("reference_name"):
		where.append("`reference_name` = %(reference_name)s")
	if conditions.get("page_route"):
		where.append("`page_route` LIKE %(page_route)s")
	if conditions.get("outcome"):
		where.append("`outcome` = %(outcome)s")
	if conditions.get("ip_address"):
		where.append("`ip_address` = %(ip_address)s")

	base = f"""
		SELECT `activity_datetime`, `user`, `activity_type`, `outcome`,
		       `reference_doctype`, `reference_name`, `page_route`, `details`,
		       `ip_address`, `source`, `changed_fields`, `attempted_user`
		FROM `{UNIFIED}`
		WHERE {' AND '.join(where)}
	"""

	if for_count:
		return f"SELECT COUNT(*) AS `total` FROM ({base}) t"

	query = f"{base} ORDER BY `activity_datetime` DESC"
	if limit:
		query += " LIMIT %(limit)s OFFSET %(offset)s"
	return query


# ----------------------------------------------------------------- route history
def route_history_query(conditions, limit=None, offset=0, for_count=False):
	where = ["`creation` BETWEEN %(from_datetime)s AND %(to_datetime)s"]
	if conditions.get("user"):
		where.append("`user` = %(user)s")
	if conditions.get("page_route"):
		where.append("`route` LIKE %(page_route)s")
	if conditions.get("activity_type"):
		where.append("'Route Visit' = %(activity_type)s")

	dedupe = _dedupe_clause("rh", "'Route Visit'", "NULL", "NULL")

	base = f"""
		SELECT `creation` AS `activity_datetime`, `user`, 'Route Visit' AS `activity_type`,
		       'Success' AS `outcome`, NULL AS `reference_doctype`, NULL AS `reference_name`,
		       `route` AS `page_route`, 'Visited page' AS `details`, NULL AS `ip_address`,
		       'Frappe' AS `source`, NULL AS `changed_fields`, NULL AS `attempted_user`
		FROM `tabRoute History` rh
		WHERE {' AND '.join(where)} AND {dedupe}
	"""

	if for_count:
		return f"SELECT COUNT(*) AS `total` FROM ({base}) t"

	query = f"{base} ORDER BY `activity_datetime` DESC"
	if limit:
		query += " LIMIT %(limit)s OFFSET %(offset)s"
	return query


# ----------------------------------------------------------------- activity log
def activity_log_query(conditions, limit=None, offset=0, for_count=False):
	where = ["`creation` BETWEEN %(from_datetime)s AND %(to_datetime)s"]
	if conditions.get("user"):
		where.append("`user` = %(user)s")
	if conditions.get("ip_address"):
		where.append("`ip_address` = %(ip_address)s")
	if conditions.get("outcome"):
		where.append("`status` = %(outcome)s")
	if conditions.get("activity_type"):
		where.append(f"({ACTIVITY_LOG_TYPE_SQL}) = %(activity_type)s")

	dedupe = _dedupe_clause(
		"al",
		ACTIVITY_LOG_TYPE_SQL,
		"NULL",
		"NULL",
		actor_expr="COALESCE(NULLIF(al.`user`, ''), al.`user`, '')",
	)

	base = f"""
		SELECT `creation` AS `activity_datetime`, `user`,
		       ({ACTIVITY_LOG_TYPE_SQL}) AS `activity_type`,
		       `status` AS `outcome`, NULL AS `reference_doctype`, NULL AS `reference_name`,
		       NULL AS `page_route`, `subject` AS `details`, `ip_address`,
		       'Frappe' AS `source`, NULL AS `changed_fields`,
		       CASE WHEN `operation` = 'Login' AND `status` = 'Failed' THEN `user` ELSE NULL END
		           AS `attempted_user`
		FROM `tabActivity Log` al
		WHERE {' AND '.join(where)} AND {dedupe}
	"""

	if for_count:
		return f"SELECT COUNT(*) AS `total` FROM ({base}) t"

	query = f"{base} ORDER BY `activity_datetime` DESC"
	if limit:
		query += " LIMIT %(limit)s OFFSET %(offset)s"
	return query


# ------------------------------------------------------------------- access log
def access_log_query(conditions, limit=None, offset=0, for_count=False):
	where = ["`creation` BETWEEN %(from_datetime)s AND %(to_datetime)s"]
	if conditions.get("user"):
		where.append("`user` = %(user)s")
	if conditions.get("activity_type"):
		where.append(f"({ACCESS_LOG_TYPE_SQL}) = %(activity_type)s")
	if conditions.get("reference_doctype"):
		where.append("IFNULL(NULLIF(`export_from`, ''), 'Report') = %(reference_doctype)s")

	dedupe = _dedupe_clause(
		"ac",
		ACCESS_LOG_TYPE_SQL,
		"IFNULL(NULLIF(`export_from`, ''), 'Report')",
		"IFNULL(NULLIF(`reference_document`, ''), `report_name`)",
	)

	base = f"""
		SELECT `creation` AS `activity_datetime`, `user`,
		       ({ACCESS_LOG_TYPE_SQL}) AS `activity_type`,
		       'Success' AS `outcome`,
		       IFNULL(NULLIF(`export_from`, ''), 'Report') AS `reference_doctype`,
		       IFNULL(NULLIF(`reference_document`, ''), `report_name`) AS `reference_name`,
		       NULL AS `page_route`,
		       CONCAT(IFNULL(`method`, ''), ' | ', IFNULL(`file_type`, ''), ' | ',
		              IFNULL(`report_name`, ''), ' | ', IFNULL(`reference_document`, '')) AS `details`,
		       NULL AS `ip_address`, 'Frappe' AS `source`, NULL AS `changed_fields`,
		       NULL AS `attempted_user`
		FROM `tabAccess Log` ac
		WHERE {' AND '.join(where)} AND {dedupe}
	"""

	if for_count:
		return f"SELECT COUNT(*) AS `total` FROM ({base}) t"

	query = f"{base} ORDER BY `activity_datetime` DESC"
	if limit:
		query += " LIMIT %(limit)s OFFSET %(offset)s"
	return query


# --------------------------------------------------------------------- view log
def view_log_query(conditions, limit=None, offset=0, for_count=False):
	where = ["`creation` BETWEEN %(from_datetime)s AND %(to_datetime)s"]
	if conditions.get("user"):
		where.append("`viewed_by` = %(user)s")
	if conditions.get("reference_doctype"):
		where.append("`reference_doctype` = %(reference_doctype)s")
	if conditions.get("reference_name"):
		where.append("`reference_name` = %(reference_name)s")
	if conditions.get("activity_type"):
		where.append("'Document View' = %(activity_type)s")

	dedupe = _dedupe_clause(
		"vl",
		"'Document View'",
		"`reference_doctype`",
		"`reference_name`",
		actor_expr="COALESCE(vl.`viewed_by`, '')",
	)

	base = f"""
		SELECT `creation` AS `activity_datetime`, `viewed_by` AS `user`,
		       'Document View' AS `activity_type`, 'Success' AS `outcome`,
		       `reference_doctype`, `reference_name`, NULL AS `page_route`,
		       'Viewed document' AS `details`, NULL AS `ip_address`,
		       'Frappe' AS `source`, NULL AS `changed_fields`, NULL AS `attempted_user`
		FROM `tabView Log` vl
		WHERE {' AND '.join(where)} AND {dedupe}
	"""

	if for_count:
		return f"SELECT COUNT(*) AS `total` FROM ({base}) t"

	query = f"{base} ORDER BY `activity_datetime` DESC"
	if limit:
		query += " LIMIT %(limit)s OFFSET %(offset)s"
	return query


# ---------------------------------------------------------------------- version
def version_query(conditions, limit=None, offset=0, for_count=False):
	where = ["`creation` BETWEEN %(from_datetime)s AND %(to_datetime)s"]
	if conditions.get("reference_doctype"):
		where.append("`ref_doctype` = %(reference_doctype)s")
	if conditions.get("reference_name"):
		where.append("`docname` = %(reference_name)s")
	if conditions.get("activity_type"):
		where.append("'Field Change' = %(activity_type)s")

	base = f"""
		SELECT `creation` AS `activity_datetime`, NULL AS `user`,
		       'Field Change' AS `activity_type`, 'Success' AS `outcome`,
		       `ref_doctype` AS `reference_doctype`, `docname` AS `reference_name`,
		       NULL AS `page_route`, 'Field level changes recorded by Frappe Version' AS `details`,
		       NULL AS `ip_address`, 'Frappe' AS `source', `data` AS `changed_fields`,
		       NULL AS `attempted_user`
		FROM `tabVersion`
		WHERE {' AND '.join(where)}
	"""

	if for_count:
		return f"SELECT COUNT(*) AS `total` FROM ({base}) t"

	query = f"{base} ORDER BY `activity_datetime` DESC"
	if limit:
		query += " LIMIT %(limit)s OFFSET %(offset)s"
	return query


# -------------------------------------------------------------------- dispatch
def _sources(conditions):
	"""قائمة المصادر المتاحة حسب الإعدادات وفلتر المصدر."""
	sources = []

	if _source_allowed(conditions, "Custom App"):
		sources.append(("unified", unified_query))

	if _source_allowed(conditions, "Frappe"):
		if config.native_source_enabled("include_native_route_history"):
			sources.append(("route_history", route_history_query))
		sources.append(("activity_log", activity_log_query))
		if config.native_source_enabled("include_native_access_log"):
			sources.append(("access_log", access_log_query))
		if config.native_source_enabled("include_native_view_log"):
			sources.append(("view_log", view_log_query))
		if config.native_source_enabled("include_native_version"):
			sources.append(("version", version_query))

	return sources


def _params(conditions, limit=None, offset=0):
	params = dict(conditions)
	if conditions.get("page_route"):
		params["page_route"] = f"%{conditions['page_route']}%"
	if limit:
		params["limit"] = int(limit)
		params["offset"] = int(offset)
	return params


def fetch_events(filters=None, start=0, page_length=100):
	"""صفحة واحدة من الأحداث، مرتّبة من الأحدث إلى الأقدم."""
	filters = frappe._dict(filters or {})
	conditions = _conditions(filters)

	# K = أعلى موضع مطلوب + حجم الصفحة؛ يجب أن يغطي كل مصدر
	k = start + page_length

	rows = []
	for _name, builder in _sources(conditions):
		query = builder(conditions, limit=k)
		rows.extend(frappe.db.sql(query, _params(conditions, limit=k, offset=0), as_dict=True))

	rows.sort(key=lambda r: (get_datetime(r.get("activity_datetime")) or get_datetime("1970-01-01")), reverse=True)

	page = rows[start : start + page_length]
	return [_format_row(r) for r in page]


def _format_row(row):
	row = frappe._dict(row)
	row["activity_datetime"] = get_datetime(row.get("activity_datetime"))
	row["changed_fields"] = _extract_changed_fields(row.get("changed_fields"))
	row["details"] = (row.get("details") or "")[:255]
	return row


def _extract_changed_fields(raw):
	"""تحويل بيانات Version (JSON) إلى أسماء الحقول المتغيّرة فقط (بلا قيم)."""
	if not raw:
		return None

	if isinstance(raw, str) and raw.strip().startswith("{"):
		import json

		try:
			data = json.loads(raw)
		except Exception:
			return str(raw)[:255]

		names = []
		for group in ("added", "changed", "removed"):
			for item in data.get(group) or []:
				if isinstance(item, list) and item:
					names.append(str(item[0]))
				elif isinstance(item, str):
					names.append(item)
		return ", ".join(dict.fromkeys(names))[:255] if names else None

	return str(raw)[:255]


def count_events(filters=None):
	"""إجمالي الأحداث المطابقة (بعد استبعاد التكرار)."""
	filters = frappe._dict(filters or {})
	conditions = _conditions(filters)

	total = 0
	for _name, builder in _sources(conditions):
		query = builder(conditions, for_count=True)
		rows = frappe.db.sql(query, _params(conditions), as_dict=True)
		total += int(rows[0]["total"]) if rows else 0

	return total


def _all_rows(filters, limit=20000):
	"""جميع الأحداث (محدود) للتحليلات الإحصائية."""
	filters = frappe._dict(filters or {})
	conditions = _conditions(filters)

	rows = []
	for _name, builder in _sources(conditions):
		query = builder(conditions, limit=limit)
		rows.extend(frappe.db.sql(query, _params(conditions, limit=limit, offset=0), as_dict=True))

	rows.sort(key=lambda r: (get_datetime(r.get("activity_datetime")) or get_datetime("1970-01-01")), reverse=True)
	return [_format_row(r) for r in rows]


def build_summary(filters=None):
	"""بطاقات الملخص الإداري داخل التقرير."""
	filters = frappe._dict(filters or {})
	rows = _all_rows(filters)

	active_users = len({r.get("user") for r in rows if r.get("user")})
	visits = sum(1 for r in rows if r.get("activity_type") == "Route Visit")
	creates = sum(1 for r in rows if r.get("activity_type") == "Document Create")
	updates = sum(1 for r in rows if r.get("activity_type") == "Document Update")
	deletes = sum(1 for r in rows if r.get("activity_type") == "Document Delete")
	failed_logins = sum(1 for r in rows if r.get("activity_type") == "Failed Login")
	prints = sum(1 for r in rows if r.get("activity_type") in ("Document Print", "Report Export"))
	denied = sum(1 for r in rows if r.get("activity_type") == "Access Denied")

	return [
		{"label": _("Total Events"), "value": len(rows), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Active Users"), "value": active_users, "datatype": "Int", "indicator": "Green"},
		{"label": _("Page Visits"), "value": visits, "datatype": "Int", "indicator": "Blue"},
		{
			"label": _("Created / Updated / Deleted"),
			"value": f"{creates} / {updates} / {deletes}",
			"datatype": "Text",
			"indicator": "Orange",
		},
		{
			"label": _("Failed Logins"),
			"value": failed_logins,
			"datatype": "Int",
			"indicator": "Red" if failed_logins else "Green",
		},
		{
			"label": _("Prints / Exports"),
			"value": prints,
			"datatype": "Int",
			"indicator": "Purple",
		},
		{
			"label": _("Access Denied"),
			"value": denied,
			"datatype": "Int",
			"indicator": "Red" if denied else "Green",
		},
	]


def build_chart(filters=None):
	"""رسم بياني: توزيع الأحداث حسب نوع النشاط."""
	filters = frappe._dict(filters or {})
	rows = _all_rows(filters)

	counts = {}
	for row in rows:
		key = row.get("activity_type") or "Other"
		counts[key] = counts.get(key, 0) + 1

	if not counts:
		return None

	return {
		"data": {
			"labels": list(counts.keys()),
			"datasets": [{"name": _("Events"), "values": list(counts.values())}],
		},
		"type": "bar",
	}
