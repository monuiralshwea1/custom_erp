# -*- coding: utf-8 -*-
"""
Workspace / desk visibility layer.

v15 calls chain (verified against installed source):
  - boot.py:load_desktop_data       → get_workspace_sidebar_items() → bootinfo.allowed_workspaces
  - frappe/apps.py:get_apps         → get_workspace_sidebar_items() (imported at call time)
  - HTTP API frappe.desk.desktop.*  → whitelisted dispatch

Python-internal (direct import) call sites are NOT covered by
override_whitelisted_methods, so this module installs a minimal, documented,
idempotent module-attribute wrapper on frappe.desk.desktop (same pattern already
established by this environment for tajer_erp). The wrapper NEVER grants access;
it only REMOVES hidden entries from the result for every user (incl.
Administrator/Workspace Manager per config).

Registered hooks:
  - boot_session      → boot_session_hook
  - override_whitelisted_methods → get_workspace_sidebar_items / get_desktop_page
"""

import frappe
from frappe.utils import cstr

PATCHED_FLAG = "_custom_erp_mc_desktop_patched"


def _lazy_state():
	from custom_erp.custom_app.module_control.visibility import get_state as gs
	return gs


def _should_filter():
	state = _lazy_state()()
	if not state["enabled"]:
		return False
	if not state["global_filter"]:
		return False
	# user-based exemption (Administrator / Workspace Manager / System Manager)
	if state["strict"]:
		return True
	from custom_erp.custom_app.module_control.visibility import user_is_exempt
	if user_is_exempt():
		return False
	return True


def _hide_unless(state, page):
	name = page.get("name")
	module = page.get("module") or (state.get("module_of_ws") or {}).get(name)
	if name and name in state["hidden_workspaces"]:
		return True
	if module and module in state["hidden_modules"]:
		return True
	# per-workspace rule with hide flag
	for row in state["workspace_rules"]:
		if row["workspace"] == name and row["hide"]:
			return True
	return False


def _filter_pages(pages):
	state = _lazy_state()()
	if not pages:
		return
	visible = []
	for page in pages:
		if _hide_unless(state, page):
			continue
		visible.append(page)
	pages[:] = visible


def _is_admin():
	return frappe.session.user == "Administrator"


def _filter_admin_only(pages):
	"""Remove admin-only workspaces for every non-Administrator user.

	Runs INDEPENDENTLY of the global filter flag / exemptions: by design these
	workspaces are invisible to all users except Administrator."""
	if not pages:
		return
	try:
		state = _lazy_state()()
		if not state.get("enabled"):
			return
		admin_wss = state.get("admin_only_workspaces") or []
		if not admin_wss or _is_admin():
			return
		from custom_erp.custom_app.module_control.visibility import admin_only_matches

		def is_admin_only(p):
			return (
				admin_only_matches(p.get("name"), admin_wss)
				or admin_only_matches(p.get("title"), admin_wss)
				or admin_only_matches(p.get("label"), admin_wss)
			)

		pages[:] = [p for p in pages if not is_admin_only(p)]
	except Exception:
		frappe.logger("module_control").error(frappe.utils.get_traceback()[:2000])


def _filter_sidebar_result(result):
	if not isinstance(result, dict):
		return
	pages = result.get("pages")
	if pages:
		_filter_pages(pages)


def wrap_get_workspace_sidebar_items(original):
	def get_workspace_sidebar_items(*args, **kwargs):
		result = original(*args, **kwargs)
		try:
			if _should_filter():
				_filter_sidebar_result(result)
			# admin-only workspaces: always enforced (independent of global filter)
			if isinstance(result, dict) and result.get("pages"):
				_filter_admin_only(result["pages"])
		except Exception:
			frappe.logger("module_control").error(frappe.utils.get_traceback()[:2000])
		return result

	get_workspace_sidebar_items._custom_erp_mc_wrapped = True
	return get_workspace_sidebar_items


def wrap_get_desktop_page(original):
	import json as _json

	def get_desktop_page(page=None, *args, **kwargs):
		try:
			# normalize page (real router sends it as a JSON string) for checks only
			name = None
			if page:
				src = page
				if isinstance(page, (str, bytes)):
					try:
						src = _json.loads(page)
					except Exception:
						src = None
				if isinstance(src, dict):
					name = src.get("name")
			if name:
				state = _lazy_state()()
				if state.get("enabled") and not _is_admin():
					from custom_erp.custom_app.module_control.visibility import admin_only_matches

					if admin_only_matches(name, state.get("admin_only_workspaces") or []):
						frappe.throw(
							frappe._("مساحة العمل {0} متاحة لمسؤول النظام (Administrator) فقط").format(frappe.bold(name)),
							frappe.PermissionError,
						)
			if _should_filter() and page and name:
				state = _lazy_state()()
				module = frappe.db.get_value("Workspace", name, "module")
				if name in state["hidden_workspaces"] or (module and module in state["hidden_modules"]):
					frappe.throw(
						frappe._("مساحة العمل {0} غير متاحة (مخفية بواسطة نظام التحكم المركزي)").format(frappe.bold(name)),
						frappe.PermissionError,
					)
				for row in state["workspace_rules"]:
					if row["workspace"] == name and row["block_nav"]:
						frappe.throw(
							frappe._("الوصول المباشر لمساحة العمل {0} محظور بواسطة نظام التحكم المركزي").format(frappe.bold(name)),
							frappe.PermissionError,
						)
		except frappe.PermissionError:
			raise
		except Exception:
			frappe.logger("module_control").error(frappe.utils.get_traceback()[:2000])
		return original(page, *args, **kwargs)

	get_desktop_page._custom_erp_mc_wrapped = True
	return get_desktop_page


def ensure_desktop_patched():
	"""Install wrappers on frappe.desk.desktop (idempotent; safe in all workers)."""
	try:
		from frappe.desk import desktop as desktop_module
	except Exception:
		return False
	if getattr(desktop_module, PATCHED_FLAG, False):
		return True
	try:
		if not hasattr(wrap_get_desktop_page, "_flagged_at_top"):
			pass
		current_sidebar = getattr(desktop_module, "get_workspace_sidebar_items", None)
		if current_sidebar is not None and not getattr(current_sidebar, "_custom_erp_mc_wrapped", False):
			setattr(desktop_module, "get_workspace_sidebar_items", wrap_get_workspace_sidebar_items(current_sidebar))
		current_pg = getattr(desktop_module, "get_desktop_page", None)
		if current_pg is not None and not getattr(current_pg, "_custom_erp_mc_wrapped", False):
			setattr(desktop_module, "get_desktop_page", wrap_get_desktop_page(current_pg))
		setattr(desktop_module, PATCHED_FLAG, True)
		return True
	except Exception:
		try:
			frappe.logger("module_control").error(frappe.utils.get_traceback()[:2000])
		except Exception:
			pass
		return False


# ---- hook entries -----------------

def boot_session_hook(bootinfo):
	"""Filter bootinfo.allowed_workspaces & module_wise_workspaces (runs on every boot build)."""
	try:
		if not bootinfo:
			return
		ensure_desktop_patched()
		if not _should_filter():
			return
		state = _lazy_state()()
		if isinstance(bootinfo.get("allowed_workspaces"), list):
			_filter_pages(bootinfo["allowed_workspaces"])
		# admin-only workspaces: enforced even for exempt users (WM/SM), except Administrator
		if isinstance(bootinfo.get("allowed_workspaces"), list):
			_filter_admin_only(bootinfo["allowed_workspaces"])
		mww = bootinfo.get("module_wise_workspaces")
		if isinstance(mww, dict):
			admin_wss = state.get("admin_only_workspaces") or []
			if admin_wss and not _is_admin():
				# values (and keys) are workspace NAME strings — match with or without the
				# private-workspace "-<user>" suffix stock Frappe appends
				from custom_erp.custom_app.module_control.visibility import admin_only_matches

				for mod in list(mww.keys()):
					if isinstance(mww.get(mod), list):
						mww[mod] = [w for w in mww[mod] if not admin_only_matches(w, admin_wss)]
			for mod in list(mww.keys()):
				if mod in state["hidden_modules"]:
					mww.pop(mod, None)
	except Exception:
		try:
			frappe.logger("module_control").error(frappe.utils.get_traceback()[:2000])
		except Exception:
			pass


# ---- official override entries ---------------------------------------------
# These delegate to the (patched) desktop functions, so filtering always applies
# exactly once. Documented override_whitelisted_methods entries in hooks.py.
# NOTE: override targets MUST be @frappe.whitelist()-ed or frappe rejects every
# request to the original path (verified: 403 "not whitelisted" without this).


@frappe.whitelist()
def get_workspace_sidebar_items_filtered(*args, **kwargs):
	# frappe.call injects `cmd` into the body; forward-only known kwargs
	kwargs.pop("cmd", None)
	kwargs.pop("lang", None)
	from frappe.desk import desktop as desktop_module
	fn = getattr(desktop_module, "get_workspace_sidebar_items", None)
	if fn is None:
		raise frappe.ImportError("frappe.desk.desktop.get_workspace_sidebar_items")
	return fn(*args, **kwargs)


@frappe.whitelist()
def get_desktop_page_filtered(page=None, *args, **kwargs):
	kwargs.pop("cmd", None)
	kwargs.pop("lang", None)
	from frappe.desk import desktop as desktop_module
	fn = getattr(desktop_module, "get_desktop_page", None)
	if fn is None:
		raise frappe.ImportError("frappe.desk.desktop.get_desktop_page")
	return fn(page, *args, **kwargs)
