# Copyright (c) 2026, moneer
# License: MIT
"""تقرير نشاط المستخدمين الموحّد (User Activity Audit Report).

يجمع الأحداث من:
1. سجل `User Activity Audit Log` (السجل الموحّد داخل custom_erp) - مصدر "Custom App".
2. السجلات الأصلية في Frappe:
   - `Route History`  - تصفّح الواجهات
   - `Activity Log`   - الدخول/الخروج/محاولات الدخول الفاشلة/الانتحال
   - `Access Log`     - الطباعة والتصدير (PDF/Excel/CSV)
   - `View Log`       - مشاهدات المستندات
   - `Version`        - التعديلات التفصيلية (أسماء الحقول المتغيّرة)

كل صف يحمل عمود `source` لتمييز مصدر الحدث، وتُعالَج التكرارات بإزالة
الأحداث المتطابقة القادمة من السجل الموحّد ونظيرها الأصلي.
"""

import frappe
from frappe import _
from frappe.utils import cint, get_datetime

from custom_erp.custom_app.audit import config, query as audit_query

REPORT_NAME = "User Activity Audit Report"


class UserActivityAuditReport:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.page_length = self.get_page_length()
		self.start = self.get_start()

	# ------------------------------------------------------------------ helpers
	def get_page_length(self):
		limit = cint(self.filters.get("page_length") or 0)
		max_rows = config.get_max_rows_per_page()
		if limit <= 0:
			limit = max_rows
		return min(limit, max(max_rows, 1))

	def get_start(self):
		page = cint(self.filters.get("page") or 1)
		if page < 1:
			page = 1
		return (page - 1) * self.page_length

	def get_columns(self):
		# ملاحظة: نستخدم Dynamic Link للوثيقة و Data لغيرها، لأن محرّك التقارير
		# في Frappe يشترط صلاحية قراءة على كل DocType يُشار إليه بحقل Link،
		# وهو ما كان يمنع دور "Audit Manager" من تشغيل التقرير.
		return [
			{
				"fieldname": "activity_datetime",
				"label": _("Date and Time"),
				"fieldtype": "Datetime",
				"width": 160,
			},
			{
				"fieldname": "user",
				"label": _("User"),
				"fieldtype": "Data",
				"width": 160,
			},
			{
				"fieldname": "activity_type",
				"label": _("Activity Type"),
				"fieldtype": "Data",
				"width": 130,
			},
			{
				"fieldname": "reference_doctype",
				"label": _("Document Type"),
				"fieldtype": "Data",
				"width": 130,
			},
			{
				"fieldname": "reference_name",
				"label": _("Document"),
				"fieldtype": "Dynamic Link",
				"options": "reference_doctype",
				"width": 180,
			},
			{
				"fieldname": "page_route",
				"label": _("Page Route"),
				"fieldtype": "Data",
				"width": 180,
			},
			{
				"fieldname": "details",
				"label": _("Description"),
				"fieldtype": "Data",
				"width": 260,
			},
			{
				"fieldname": "outcome",
				"label": _("Outcome"),
				"fieldtype": "Data",
				"width": 90,
			},
			{
				"fieldname": "ip_address",
				"label": _("IP Address"),
				"fieldtype": "Data",
				"width": 130,
			},
			{
				"fieldname": "source",
				"label": _("Event Source"),
				"fieldtype": "Data",
				"width": 100,
			},
			{
				"fieldname": "attempted_user",
				"label": _("Attempted User"),
				"fieldtype": "Data",
				"width": 150,
			},
			{
				"fieldname": "changed_fields",
				"label": _("Changed Fields"),
				"fieldtype": "Data",
				"width": 220,
			},
		]

	def get_data(self):
		return audit_query.fetch_events(self.filters, start=self.start, page_length=self.page_length)

	def get_count(self):
		return audit_query.count_events(self.filters)

	def get_report_summary(self):
		return audit_query.build_summary(self.filters)

	def get_chart(self):
		return audit_query.build_chart(self.filters)

	def run(self):
		columns = self.get_columns()
		data = self.get_data()
		total = self.get_count()
		summary = self.get_report_summary()
		chart = self.get_chart()

		shown_from = self.start + 1 if total else 0
		shown_to = min(self.start + self.page_length, total)

		message = {
			"message": _("{0} event(s) matched - showing {1} to {2}.").format(
				total, shown_from, shown_to
			),
			"indicator": "blue",
		}

		return columns, data, message, chart, summary


def execute(filters=None):
	"""نقطة الدخول من محرّك التقارير في Frappe."""
	return UserActivityAuditReport(filters).run()
