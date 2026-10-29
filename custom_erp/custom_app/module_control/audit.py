# -*- coding: utf-8 -*-
"""Audit logging helpers for Central Module Control Manager."""
import frappe

AUDIT_DOCTYPE = "Module Control Audit Log"


def log(source, target_type, target_name, old_state, new_state, status="Success", details=None):
	"""Write one audit row. Failures are logged, never raised (audit must not break core work)."""
	try:
		settings_enable = frappe.db.get_single_value("Module Control Settings", "enable_audit_logging")
		if not settings_enable:
			return
		frappe.get_doc(
			{
				"doctype": AUDIT_DOCTYPE,
				"user": frappe.session.user,
				"timestamp": frappe.utils.now_datetime(),
				"target_type": target_type or "",
				"target_name": target_name or "",
				"old_state": frappe.utils.cstr(old_state)[:1000] if old_state is not None else "",
				"new_state": frappe.utils.cstr(new_state)[:1000] if new_state is not None else "",
				"source": source or "Unknown",
				"status": status or "Success",
				"details": (details or "")[:1000],
			}
		).insert(ignore_permissions=True, ignore_links=True, set_name="hash", set_child_names=False)
	except Exception:
		try:
			frappe.logger("module_control_audit").error(frappe.utils.get_traceback()[:2000])
		except Exception:
			pass


def log_many(source, events):
	"""events: list of dicts with keys target_type/target_name/old_state/new_state/status/details."""
	for ev in events or []:
		log(
			source,
			ev.get("target_type"),
			ev.get("target_name"),
			ev.get("old_state"),
			ev.get("new_state"),
			ev.get("status") or "Success",
			ev.get("details"),
		)


def log_failure(source, details):
	log(source, "System", "-", "-", "-", status="Failure", details=details)
