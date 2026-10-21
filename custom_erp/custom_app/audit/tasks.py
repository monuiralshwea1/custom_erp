# Copyright (c) 2026, moneer
# License: MIT
"""مهام مجدولة نظام مراقبة نشاط المستخدمين."""

import frappe
from frappe.utils import add_days, getdate, now_datetime

from custom_erp.custom_app.audit import config


def purge_expired_audit_logs():
	"""حذف سجلات التدقيق الأقدم من مدة الاحتفاظ.

	- لا يُحذف أي سجل إذا كانت سياسة الاحتفاظ غير محددة (retention_days = 0).
	- تُعتمد السجلات الأصلية في Frappe (Route History / Activity Log / Access Log)
	  عبر `Log Settings` في Frappe ولا نتدخل في ذلك هنا.
	"""
	if not config.is_enabled():
		return

	retention_days = config.get_retention_days()
	if not retention_days:
		return

	cutoff = add_days(getdate(now_datetime()), -int(retention_days))

	deleted = frappe.db.sql(
		"DELETE FROM `tabUser Activity Audit Log` WHERE `creation` < %s",
		(str(cutoff),),
	)
	frappe.db.commit()

	if deleted:
		frappe.logger().info(
			"User Activity Audit: purged {0} record(s) older than {1}".format(deleted, cutoff)
		)
