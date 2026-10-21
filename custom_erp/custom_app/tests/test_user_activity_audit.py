# Copyright (c) 2026, moneer
# License: MIT
"""ط§ط®طھط¨ط§ط±ط§طھ ظ†ط¸ط§ظ… ظ…ط±ط§ظ‚ط¨ط© ظ†ط´ط§ط· ط§ظ„ظ…ط³طھط®ط¯ظ…ظٹظ†."""

import frappe
from frappe.tests.utils import FrappeTestCase

from custom_erp.custom_app.audit import config, logger
from custom_erp.custom_app.audit.document_events import get_changed_fields


class TestUserActivityAudit(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.settings = frappe.get_single("User Activity Audit Settings")
		self.settings.enabled = 1
		self.settings.capture_document_events = 1
		self.settings.capture_login_events = 1
		self.settings.capture_request_events = 1
		self.settings.capture_route_visits = 1
		self.settings.route_dedupe_seconds = 60
		self.settings.sensitive_field_patterns = (
			"password, passwd, pwd, secret, token, api_key, api_secret, "
			"private_key, signature, otp, credential"
		)
		# كل اختبار مستقل: إزالة أي استثناءات أضافها اختبار سابق
		for row in list(self.settings.excluded_doctypes or []):
			self.settings.remove(row)
		for row in list(self.settings.excluded_fields or []):
			self.settings.remove(row)
		self.settings.save(ignore_permissions=True)
		config.clear_settings_cache()

	def _count(self, filters=None):
		return frappe.db.count("User Activity Audit Log", filters or {})

	def _last(self, filters=None, order_by="creation desc"):
		rows = frappe.get_all(
			"User Activity Audit Log",
			filters=filters or {},
			fields=["name", "user", "activity_type", "outcome", "reference_doctype",
					"reference_name", "page_route", "details", "ip_address", "source",
					"changed_fields", "attempted_user"],
			order_by=order_by,
			limit=1,
			ignore_permissions=True,
		)
		return rows[0] if rows else None

	# ------------------------------------------------------------------ logging
	def test_document_create_is_logged(self):
		doc = frappe.get_doc({"doctype": "ToDo", "description": "audit-test-todo"})
		doc.insert(ignore_permissions=True)

		rows = self._all_for(doc.name)
		self.assertEqual(len(rows), 1, f"expected exactly one event, got {rows}")
		row = rows[0]
		self.assertEqual(row["activity_type"], "Document Create")
		self.assertEqual(row["reference_doctype"], "ToDo")
		self.assertEqual(row["source"], "Custom App")

	def _all_for(self, reference_name):
		return frappe.get_all(
			"User Activity Audit Log",
			filters={"reference_name": reference_name},
			fields=["name", "user", "activity_type", "outcome", "reference_doctype",
					"reference_name", "source", "details", "changed_fields"],
			order_by="creation asc",
			ignore_permissions=True,
		)

	def test_document_update_is_logged_with_changed_fields(self):
		doc = frappe.get_doc({"doctype": "ToDo", "description": "audit-test-update"})
		doc.insert(ignore_permissions=True)
		doc.description = "audit-test-updated"
		doc.save(ignore_permissions=True)

		row = self._last({"reference_name": doc.name, "activity_type": "Document Update"})
		self.assertIsNotNone(row)
		self.assertIn("description", (row["changed_fields"] or ""))

	def test_document_delete_is_logged(self):
		doc = frappe.get_doc({"doctype": "ToDo", "description": "audit-test-delete"})
		doc.insert(ignore_permissions=True)
		name = doc.name
		doc.delete()

		row = self._last({"reference_name": name})
		self.assertIsNotNone(row)
		self.assertEqual(row["activity_type"], "Document Delete")

	def test_audit_log_does_not_block_document_deletion(self):
		"""سجل التدقيق يجب ألا يمنع حذف المستند المُوثَّق."""
		doc = frappe.get_doc({"doctype": "ToDo", "description": "audit-test-nolink"})
		doc.insert(ignore_permissions=True)
		name = doc.name

		self.assertTrue(self._all_for(name), "audit record should exist")

		# الحذف يجب أن ينجح رغم وجود سجل تدقيق مرتبط بالمستند
		doc.reload()
		doc.delete()
		self.assertFalse(frappe.db.exists("ToDo", name))

	def test_login_event_is_logged(self):
		from custom_erp.custom_app.audit.auth_events import on_login

		before = self._count()
		on_login()

		self.assertGreaterEqual(self._count(), before)
		row = self._last({"activity_type": "Login"})
		self.assertIsNotNone(row)
		self.assertEqual(row["source"], "Custom App")

	def test_failed_login_is_logged_with_attempted_user(self):
		from custom_erp.custom_app.audit.auth_events import log_failed_login

		log_failed_login("not_a_real_user@example.com", reason="Invalid credentials")
		row = self._last({"activity_type": "Failed Login"})
		self.assertIsNotNone(row)
		self.assertEqual(row["attempted_user"], "not_a_real_user@example.com")
		self.assertEqual(row["outcome"], "Failure")

	# ------------------------------------------------------------------ identity
	def test_user_cannot_be_forged(self):
		"""يجب أن يتغلب الخادم على اسم المستخدم المُرسل."""
		other_user = "audit-forgery-test@example.com"
		created_user = False
		if not frappe.db.exists("User", other_user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": other_user,
					"first_name": "Audit",
					"last_name": "Forgery",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
			created_user = True

		try:
			doc = frappe.get_doc(
				{
					"doctype": "User Activity Audit Log",
					"user": other_user,
					"activity_type": "Other",
					"outcome": "Success",
					"source": "Custom App",
				}
			)
			doc.insert(ignore_permissions=True)
			self.assertEqual(doc.user, frappe.session.user)
		finally:
			if created_user:
				frappe.delete_doc("User", other_user, ignore_permissions=True, force=True)

	def test_audit_log_is_not_logged_again(self):
		before = self._count()
		doc = frappe.get_doc(
			{
				"doctype": "User Activity Audit Log",
				"activity_type": "Other",
				"outcome": "Success",
				"source": "Custom App",
			}
		)
		doc.insert(ignore_permissions=True)
		# ظٹط¬ط¨ ط£ظ„ط§ ظٹظ†ط´ط£ ط³ط¬ظ„ ط¬ط¯ظٹط¯ ظ„طھط¯ظˆظٹظ† ط§ظ„ط³ط¬ظ„ ظ†ظپط³ظ‡
		self.assertEqual(self._count(), before + 1)

	# ------------------------------------------------------------------ sensitive
	def test_sensitive_field_names_are_not_logged(self):
		self.settings.sensitive_field_patterns = "description, secret_field"
		self.settings.save(ignore_permissions=True)
		config.clear_settings_cache()

		doc = frappe.get_doc({"doctype": "ToDo", "description": "audit-test-sensitive"})
		doc.insert(ignore_permissions=True)
		doc.description = "audit-test-sensitive-2"
		doc.save(ignore_permissions=True)

		row = self._last({"reference_name": doc.name, "activity_type": "Document Update"})
		self.assertIsNotNone(row)
		self.assertNotIn("description", (row["changed_fields"] or ""))

	def test_changed_fields_never_contain_values(self):
		doc = frappe.get_doc({"doctype": "ToDo", "description": "audit-test-values"})
		doc.insert(ignore_permissions=True)
		doc.description = "super-secret-value-123"
		doc.save(ignore_permissions=True)

		row = self._last({"reference_name": doc.name, "activity_type": "Document Update"})
		self.assertNotIn("super-secret-value-123", (row["changed_fields"] or ""))

	# ------------------------------------------------------------------ dedupe
	def test_route_dedupe_prevents_duplicate_logging(self):
		key = "test-dedupe-key"
		frappe.cache().delete_value(f"audit_dedupe:{key}")

		first = logger.should_dedupe(key, 60)
		second = logger.should_dedupe(key, 60)

		self.assertFalse(first)
		self.assertTrue(second)
		frappe.cache().delete_value(f"audit_dedupe:{key}")

	# ------------------------------------------------------------------ settings
	def test_excluded_doctype_is_not_logged(self):
		self.settings.append(
			"excluded_doctypes", {"excluded_doctype": "ToDo", "reason": "automated test"}
		)
		self.settings.save(ignore_permissions=True)
		config.clear_settings_cache()

		doc = frappe.get_doc({"doctype": "ToDo", "description": "audit-test-excluded"})
		doc.insert(ignore_permissions=True)

		self.assertEqual(self._all_for(doc.name), [])

	def test_disabled_audit_logs_nothing(self):
		self.settings.enabled = 0
		self.settings.save(ignore_permissions=True)
		config.clear_settings_cache()

		doc = frappe.get_doc({"doctype": "ToDo", "description": "audit-test-disabled"})
		doc.insert(ignore_permissions=True)

		self.assertEqual(self._all_for(doc.name), [])

		self.settings.enabled = 1
		self.settings.save(ignore_permissions=True)
		config.clear_settings_cache()

	# ------------------------------------------------------------------ report
	def test_report_returns_columns_and_rows(self):
		from custom_erp.custom_app.report.user_activity_audit_report.user_activity_audit_report import (
			execute,
		)

		doc = frappe.get_doc({"doctype": "ToDo", "description": "audit-test-report"})
		doc.insert(ignore_permissions=True)

		# نرشّح بالمستخدم ونوع النشاط لنضمن ظهور سجلنا ضمن الصفحة الأولى
		columns, data, message, chart, summary = execute(
			{
				"from_date": frappe.utils.add_days(frappe.utils.nowdate(), -1),
				"to_date": frappe.utils.add_days(frappe.utils.nowdate(), 1),
				"activity_type": "Document Create",
				"page_length": 500,
				"page": 1,
			}
		)

		self.assertTrue(columns)
		self.assertIn("activity_type", [c["fieldname"] for c in columns])
		self.assertIn("source", [c["fieldname"] for c in columns])
		self.assertIsInstance(data, list)
		self.assertIsInstance(summary, list)
		self.assertTrue(any(r["reference_name"] == doc.name for r in data))
		# كل الصفوف يجب أن تحمل مصدراً محدداً
		self.assertTrue(all(r.get("source") in ("Custom App", "Frappe") for r in data))

	def test_report_pagination_limits_rows(self):
		from custom_erp.custom_app.report.user_activity_audit_report.user_activity_audit_report import (
			execute,
		)

		for i in range(5):
			doc = frappe.get_doc({"doctype": "ToDo", "description": f"audit-test-page-{i}"})
			doc.insert(ignore_permissions=True)

		filters = {
			"from_date": frappe.utils.add_days(frappe.utils.nowdate(), -1),
			"to_date": frappe.utils.add_days(frappe.utils.nowdate(), 1),
			"page_length": 3,
			"page": 1,
		}
		columns, data, message, chart, summary = execute(filters)
		self.assertLessEqual(len(data), 3)

	# ------------------------------------------------------------------ permissions
	def test_normal_user_cannot_read_audit_log(self):
		"""ط§ظ„ظ…ط³طھط®ط¯ظ… ط§ظ„ط¹ط§ط¯ظٹ ظ„ط§ ظٹظ…ظ„ظƒ طµظ„ط§ط­ظٹط© ظ‚ط±ط§ط،ط© ط³ط¬ظ„ط§طھ ط§ظ„طھط¯ظ‚ظٹظ‚."""
		perms = frappe.get_all(
			"DocPerm",
			filters={"parent": "User Activity Audit Log"},
			fields=["role", "read", "write", "create", "delete", "report", "export"],
		)
		roles = {p["role"] for p in perms}
		self.assertIn("System Manager", roles)
		self.assertIn("Audit Manager", roles)
		self.assertNotIn("All", roles)
		self.assertNotIn("System User", roles)

		# ظ„ط§ طھظˆط¬ط¯ طµظ„ط§ط­ظٹط© ظƒطھط§ط¨ط©/ط¥ظ†ط´ط§ط،/ط­ط°ظپ ظ„ط£ظٹ ط¯ظˆط± ط¹ط§ط¯ظٹ
		for p in perms:
			if p["role"] in ("System Manager", "Audit Manager"):
				continue
			self.assertFalse(p["create"], f"{p['role']} must not create audit records")
			self.assertFalse(p["write"], f"{p['role']} must not modify audit records")
			self.assertFalse(p["delete"], f"{p['role']} must not delete audit records")


