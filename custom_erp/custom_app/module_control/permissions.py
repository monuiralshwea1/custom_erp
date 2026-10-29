# -*- coding: utf-8 -*-
"""
Access-blocking layer (server-side) for Central Module Control Manager.

Verified v15 facts (source inspected on installed frappe):
  - frappe.permissions.has_permission() short-circuits user == "Administrator"
    BEFORE any hooks → access blocking can NOT apply to Administrator at core
    level. This is documented as a hard limitation; visual hiding still applies.
  - Doc-level rejections go through permissions.get_doc_permissions →
    has_controller_permissions → has_permission hooks (doctype + "*").
  - List/query rejections go through frappe.model.db_query.get_permission_query_conditions
    → permission_query_conditions hooks (doctype + "*").

Hooks registered here:
  has_permission["*"]                  → has_permission_hook
  permission_query_conditions["*"]     → query_conditions_hook
  before_request                       → before_request_hook (path-based guard:
                                          /api/resource/{doctype} and
                                          /api/method/{app}.* when enabled)

What is NOT covered (documented honestly):
  - frappe.get_all(..., ignore_permissions=True) and direct SQL.
  - Administrator (core bypass).
"""

import frappe
from frappe.utils import cint, cstr

STYPES = ("read", "write", "create", "delete", "submit", "cancel", "amend", "import", "email", "print")

# واجهات «إدارة التطوير»: مستنداتنا التي لا يدخلها إلا Administrator،
# بلا اعتبار لأي إعدادات أو أدوار أو وضع صارم (مثل admin_only_workspaces).
DEV_ACCESS_MESSAGE = "ليس لك إذن الوصول لهذه الصفحة — خاصة بالمطوّر (أدوارها متاحة لحساب Administrator فقط)"

DEV_DOCTYPES = (
	"Module Control Settings",
	"Module Control Rule",
	"Workspace Control Rule",
	"Module Control Audit Log",
)


def _is_dev_doctype(doctype):
	return cstr(doctype or "").strip() in DEV_DOCTYPES


def _lazy_state():
	from custom_erp.custom_app.module_control.visibility import get_state
	return get_state


def _access_on(user=None):
	"""Is access blocking active for this user (Administrator excluded by core anyway)?"""
	state = _lazy_state()()
	if not state["enabled"] or not state["access_blocking"]:
		return False
	return True


def _dev_deny(doctype, user, ptype=None):
	"""Reject access mirroring Frappe core's getdoc pattern (desk/form/load.py):
	set frappe.flags.error_message so the response carries `_error_message` —
	the desk client shows this exact text in the 403 msgprint card."""
	frappe.flags.error_message = frappe._(DEV_ACCESS_MESSAGE)
	raise frappe.PermissionError(frappe._(DEV_ACCESS_MESSAGE))


def has_permission_hook(doc=None, ptype="read", user=None, **kwargs):
	"""Doc-level controller hook (permissions.get_doc_permissions)."""
	try:
		if frappe.flags.get("mc_bypass"):
			return None
		user = user or frappe.session.user
		# DEV-ONLY gate (independent of settings): «إدارة التطوير» DocTypes
		if _is_dev_doctype(getattr(doc, "doctype", None) if doc is not None else None):
			if user != "Administrator" and ptype in STYPES:
				_dev_deny(getattr(doc, "doctype"), user, ptype)
			return None
		if user == "Administrator":
			return None
		if not _access_on(user):
			return None
		doctype = cstr(getattr(doc, "doctype", "") or "")
		if not doctype:
			return None
		state = _lazy_state()()

		if doctype == "Workspace":
			name = cstr(getattr(doc, "name", "") or "")
			blocked = name in state["hidden_workspaces"] or name in state["block_nav_workspaces"]
			if not blocked:
				mod = cstr(getattr(doc, "module", "") or "")
				blocked = (mod in state["hidden_modules"])
			if blocked and ptype in STYPES:
				return False
			return None

		if doctype in state["blocked_doctypes"] and ptype in STYPES:
			return False

		# Page/Report instances: block if owner module is blocked
		if doctype in ("Page", "Report"):
			owner = state["page_owner" if doctype == "Page" else "report_owner"].get(cstr(getattr(doc, "name", "")))
			if owner and owner in state["blocked_modules"] and ptype in STYPES:
				return False
		return None
	except frappe.PermissionError:
		raise
	except Exception:
		# Deny nothing on our own failure — never break normal access checks
		try:
			frappe.logger("module_control").error(frappe.utils.get_traceback()[:2000])
		except Exception:
			pass
		return None


def query_conditions_hook(user=None, doctype=None):
	"""List-level SQL filter (db_query). Returning "1=0" hides ALL rows for blocked doctypes."""
	try:
		if frappe.flags.get("mc_bypass"):
			return None
		user = user or frappe.session.user
		# DEV-ONLY gate (independent of settings): refusing the list itself
		if _is_dev_doctype(doctype) and user != "Administrator":
			_dev_deny(doctype, user)
		if user == "Administrator":
			return None
		state = _lazy_state()()
		if not state["enabled"] or not state["access_blocking"]:
			return None
		t = cstr(doctype or "")
		if t and t in state["blocked_doctypes"]:
			return "1=0"
		return None
	except frappe.PermissionError:
		raise
	except Exception:
		try:
			frappe.logger("module_control").error(frappe.utils.get_traceback()[:2000])
		except Exception:
			pass
		return None


def before_request_hook():
	"""Path-based guard (runs before dispatch).
	Blocks:
	  /api/resource/{doctype}          when doctype blocked
	  /api/method/{app_name}.{...}     when the owning app of a blocked module requested
	                                   block_protected_apis and scope == "app"
	Exception, not HTML injection: raises frappe.PermissionError → HTTP 403.
	"""
	try:
		req = getattr(frappe.local, "request", None)
		if req is None:
			return
		user = frappe.session.user if getattr(frappe, "session", None) else "Guest"
		path = frappe.utils.cstr(getattr(req, "path", "") or "")

		# DEV-ONLY gate (independent of settings): /api/resource for our dev doctypes
		if user != "Administrator" and path.startswith("/api/resource/"):
			from urllib.parse import unquote
			parts = unquote(path[len("/api/resource/"):])
			doctype = frappe.utils.cstr(parts.split("/", 1)[0])
			if _is_dev_doctype(doctype):
				_dev_deny(doctype, user)

		state = _lazy_state()()
		if not state["enabled"] or not state["access_blocking"]:
			return
		if user == "Administrator":
			return

		# /api/method/... takes precedence (BI / REST handled there too in v13+)
		if path.startswith("/api/method/"):
			method = path[len("/api/method/"):]
			if state["protected_api_scope"] == "app" and state["protected_apps"]:
				prefix = method.split(".", 1)[0]
				if prefix and prefix in state["protected_apps"]:
					# allow the QMS of our own app and audit endpoints
					if method.startswith("custom_erp."):
						return
					raise frappe.PermissionError(
						frappe._("تم حظر مسار API هذا بواسطة نظام التحكم المركزي في الموديولات")
					)
			return

		if path.startswith("/api/resource/"):
			from urllib.parse import unquote
			# unquote covers %20-style names like "Module Control %20Rule"
			parts = unquote(path[len("/api/resource/"):])
			doctype = frappe.utils.cstr(parts.split("/", 1)[0])
			if doctype and doctype in state["blocked_doctypes"]:
				raise frappe.PermissionError(
					frappe._("المستندات {0} محظورة بواسطة نظام التحكم المركزي في الموديولات").format(
						frappe.bold(doctype)
					)
				)
		return
	except frappe.PermissionError:
		raise
	except Exception:
		try:
			frappe.logger("module_control").error(frappe.utils.get_traceback()[:2000])
		except Exception:
			pass
