# Copyright (c) 2026, moneer
# License: MIT
"""التقاط أحداث دورة حياة المستندات (إنشاء/تعديل/حذف/اعتماد/إلغاء/تعديل بعد اعتماد)."""

import frappe

from custom_erp.custom_app.audit import config, logger

# حقول لا تُقارن (جداول ومعاملات تخطيط) لتقليل الحمل على العمليات اليومية
SKIP_FIELDTYPES = {
	"Table",
	"Table MultiSelect",
	"Section Break",
	"Column Break",
	"HTML",
	"Button",
	"Fold",
	"Heading",
	"Tab Break",
}


def _before_save(doc):
	try:
		return doc.get_doc_before_save()
	except Exception:
		return getattr(doc, "_doc_before_save", None)


def get_changed_fields(doc):
	"""أسماء الحقول التي تغيّرت فقط (بلا أي قيم)."""
	before = _before_save(doc)
	if not before:
		return []

	changed = []
	try:
		fields = doc.meta.fields
	except Exception:
		return []

	for df in fields:
		if df.fieldtype in SKIP_FIELDTYPES:
			continue
		fieldname = df.fieldname
		if not fieldname or df.fieldname.startswith("_"):
			continue
		if config.is_sensitive_field(doc.doctype, fieldname):
			# الحقول الحسّاسة لا يُسجَّل حتى اسمها
			continue
		try:
			old_value = before.get(fieldname)
			new_value = doc.get(fieldname)
		except Exception:
			continue
		if old_value != new_value:
			changed.append(fieldname)

	return changed


def _doc_details(doc, extra=None):
	parts = []
	if doc.get("amended_from"):
		parts.append(frappe._("Amended from {0}").format(doc.get("amended_from")))
	if doc.get("docstatus") == 1:
		parts.append(frappe._("Submitted document"))
	if extra:
		parts.append(extra)
	return " - ".join(parts) if parts else None


def _is_fresh_insert(doc):
	"""هل هذا المستند أُنشئ للتو؟

	عند الإنشاء تُستدعى `after_insert` ثم `on_update` معاً، لذلك نتجاهل
	`on_update` في هذه الحالة حتى لا يُسجَّل الحدث مرتين.
	"""
	return bool(getattr(doc, "flags", None) and doc.flags.get("in_insert"))


def handle_after_insert(doc, method=None):
	if not config.capture_enabled("document"):
		return
	if config.should_skip_doctype(doc.doctype):
		return

	activity_type = "Document Amend" if doc.get("amended_from") else "Document Create"
	logger.log_activity(
		activity_type,
		outcome="Success",
		reference_doctype=doc.doctype,
		reference_name=doc.name,
		details=_doc_details(doc),
		changed_fields=None,
	)


def handle_on_update(doc, method=None):
	if not config.capture_enabled("document"):
		return
	if config.should_skip_doctype(doc.doctype):
		return

	# عند الإنشاء تم تسجيل "Document Create" بالفعل في after_insert
	if _is_fresh_insert(doc):
		return

	before = _before_save(doc)
	before_status = before.docstatus if before else 0

	# انتقال إلى الاعتماد: يتولّاه on_submit لتفادي ازدواج السجل
	if doc.docstatus == 1 and before_status == 0:
		return

	details = None
	activity_type = "Document Update"
	if doc.docstatus == 1 and before_status == 1:
		details = frappe._("Modified after submit")

	logger.log_activity(
		activity_type,
		outcome="Success",
		reference_doctype=doc.doctype,
		reference_name=doc.name,
		details=_doc_details(doc, details),
		changed_fields=get_changed_fields(doc),
	)


def handle_on_submit(doc, method=None):
	if not config.capture_enabled("document"):
		return
	if config.should_skip_doctype(doc.doctype):
		return

	logger.log_activity(
		"Document Submit",
		outcome="Success",
		reference_doctype=doc.doctype,
		reference_name=doc.name,
		details=_doc_details(doc),
	)


def handle_on_cancel(doc, method=None):
	if not config.capture_enabled("document"):
		return
	if config.should_skip_doctype(doc.doctype):
		return

	logger.log_activity(
		"Document Cancel",
		outcome="Success",
		reference_doctype=doc.doctype,
		reference_name=doc.name,
		details=_doc_details(doc),
	)


def handle_on_trash(doc, method=None):
	if not config.capture_enabled("document"):
		return
	if config.should_skip_doctype(doc.doctype):
		return

	logger.log_activity(
		"Document Delete",
		outcome="Success",
		reference_doctype=doc.doctype,
		reference_name=doc.name,
		details=frappe._("Document deleted"),
	)
