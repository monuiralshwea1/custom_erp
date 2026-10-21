# Copyright (c) 2026, moneer
# License: MIT

import frappe
from frappe.model.document import Document
from frappe.utils import now

# السجل الذي لا يُسمح بتسجيله داخل نفسه (منع الحلقات المتكررة)
SELF_DOCTYPE = "User Activity Audit Log"


class UserActivityAuditLog(Document):
	"""سجل موحّد لنشاط المستخدمين.

	- القراءة فقط بالنسبة للمستخدمين العاديين (لا توجد صلاحية insert/delete).
	- هوية المستخدم تُحدَّد من الجلسة الموثّقة على الخادم ولا تُؤخذ من المتصفح.
	"""

	def before_insert(self):
		self.set_server_identity()
		self.set_default_values()

	def validate(self):
		self.set_server_identity()

	def on_trash(self):
		"""منع حذف سجلات التدقيق إلا بصلاحية إدارية صريحة، مع توثيق عملية الحذف."""
		if frappe.flags.get("allow_audit_log_delete"):
			return

		if frappe.session.user not in ("Administrator",):
			frappe.throw(
				frappe._("Deleting audit records is not allowed. Set `allow_audit_log_delete` flag to override."),
				frappe.PermissionError,
			)

		# توثيق عملية حذف سجل التدقيق نفسه (بدون استدعاء المسار العام لتفادي التكرار)
		frappe.db.sql(
			"""
			INSERT INTO `tabUser Activity Audit Log`
				(`name`, `creation`, `modified`, `modified_by`, `owner`, `docstatus`, `idx`,
				 `naming_series`, `user`, `activity_datetime`, `activity_type`, `outcome`,
				 `reference_doctype`, `reference_name`, `details`, `source`, `correlation_id`)
			VALUES
				(%(name)s, %(creation)s, %(creation)s, %(modified_by)s, %(owner)s, 0, 0,
				 %(naming_series)s, %(user)s, %(creation)s, 'Other', 'Success',
				 'User Activity Audit Log', %(deleted_name)s, %(details)s, 'Custom App', %(correlation_id)s)
			""",
			{
				"name": frappe.generate_hash(length=12),
				"creation": now(),
				"modified_by": frappe.session.user,
				"owner": frappe.session.user,
				"naming_series": "UAL-.YYYY.-",
				"user": frappe.session.user,
				"deleted_name": self.name,
				"details": frappe._("Audit record deleted by {0}").format(frappe.session.user),
				"correlation_id": frappe.generate_hash(length=12),
			},
		)

	def set_server_identity(self):
		"""المستخدم المسجَّل يُؤخذ من الجلسة الموثّقة فقط (لا يُقبل من المتصفح)."""
		session_user = frappe.session.user
		if session_user and session_user != "Guest":
			self.user = session_user

	def set_default_values(self):
		if not self.activity_datetime:
			self.activity_datetime = now()
		if not self.outcome:
			self.outcome = "Success"
		if not self.source:
			self.source = "Custom App"
		if not self.correlation_id:
			self.correlation_id = frappe.generate_hash(length=12)


@frappe.whitelist()
def get_audit_log_count(filters=None):
	"""عدد السجلات مطابقاً للفلاتر (يُستخدم في ترقيم صفحات التقرير)."""
	from custom_erp.custom_app.audit.query import count_audit_logs

	if not frappe.has_permission(SELF_DOCTYPE, "read"):
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)

	return count_audit_logs(filters)
