# Copyright (c) 2026, moneer
# License: MIT
"""إعدادات نظام مراقبة نشاط المستخدمين."""

import frappe
from frappe.model.document import Document


class UserActivityAuditSettings(Document):
	def validate(self):
		if self.retention_days is not None and self.retention_days < 0:
			frappe.throw(frappe._("Retention days cannot be negative."))

		if self.max_rows_per_page and self.max_rows_per_page < 10:
			frappe.throw(frappe._("Maximum rows per page must be at least 10."))

	def on_update(self):
		# إلغاء ذاكرة التخزين المؤقتة لإعدادات التدقيق
		from custom_erp.custom_app.audit import config

		config.clear_settings_cache()
