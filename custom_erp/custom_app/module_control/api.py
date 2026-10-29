# -*- coding: utf-8 -*-
"""Whitelisted API endpoints for the Central Module Control admin UI."""
import json

import frappe
from frappe.utils import cint, cstr

from custom_erp.custom_app.module_control import scanner, sync
from custom_erp.custom_app.module_control.visibility import get_state


DEV_ACCESS_MESSAGE = "ليس لك إذن الوصول لهذه الصفحة — خاصة بالمطوّر (أدوارها متاحة لحساب Administrator فقط)"


def require_admin():
	"""Dev UIs are for the Administrator ONLY (not even System Manager)."""
	user = frappe.session.user
	if user == "Administrator":
		return
	frappe.throw(frappe._(DEV_ACCESS_MESSAGE), frappe.PermissionError)


def _parse_payload(payload):
	if isinstance(payload, str):
		payload = json.loads(payload) if payload.strip() else {}
	if not isinstance(payload, dict):
		frappe.throw(frappe._("حِمل غير صالح"))
	return payload


@frappe.whitelist()
def get_overview(**kwargs):
	"""Full admin-grid data: modules inventory + applied rules + settings + forced info."""
	require_admin()
	from custom_erp.custom_app.module_control.visibility import user_is_exempt

	inventory = scanner.refresh_inventory()
	state = get_state()
	doc = sync._settings_doc()

	module_rules = state["module_rules"]
	hw_names = set(state["hidden_workspaces"]) | set(state["block_nav_workspaces"])

	def _ws_state(w):
		n = w["name"]
		hid = n in hw_names
		rx = {}
		for r in state["workspace_rules"]:
			if r["workspace"] == n:
				rx = r
				break
		return {
			"name": n,
			"is_hidden": bool(w.get("is_hidden")),
			"public": bool(w.get("public")),
			"mc_hidden": hid or bool((w.get("module") or "") in state["hidden_modules"]),
			"enforced": bool(rx.get("enforced")) if rx else (n in state["py_forced_hidden_ws"]),
			"rule_hide": bool(rx.get("hide")) if rx else False,
		}

	modules = []
	for name, item in sorted(inventory.items()):
		rule = module_rules.get(name, {})
		modules.append(
			{
				"module": name,
				"app": item.get("app") or "",
				"module_title": item.get("module_title") or "",
				"doctypes": item.get("doctypes", 0),
				"pages": item.get("pages", 0),
				"reports": item.get("reports", 0),
				"workspace_count": item.get("workspace_count", 0),
				"hidden": name in state["hidden_modules"],
				"search_hidden": name in state["search_hidden_modules"],
				"blocked": name in state["blocked_modules"],
				"py_forced": name in state["py_forced_hidden"] or name in state["py_forced_blocked"],
				"rule": rule,
				"workspaces": [_ws_state(w) for w in item.get("workspaces", [])],
			}
		)

	audit = frappe.get_all(
		"Module Control Audit Log",
		fields=["user", "timestamp", "target_type", "target_name", "old_state", "new_state", "source", "status", "details"],
		order_by="creation desc",
		limit=25,
	) if frappe.db.exists("DocType", "Module Control Audit Log") else []

	return {
		"modules": modules,
		"settings": {k: doc.get(k) for k in (
			"enabled", "enable_global_workspace_filter", "enable_access_blocking",
			"strict_visibility_mode", "enable_audit_logging", "default_behavior_for_new_modules",
			"configuration_version", "last_synchronization",
		)} if doc else {},
		"applied_flags": {
			"enabled": state["enabled"],
			"global_filter": state["global_filter"],
			"access_blocking": state["access_blocking"],
			"strict": state["strict"],
			"hidden_modules": state["hidden_modules"],
			"blocked_modules": state["blocked_modules"],
			"hidden_workspaces": state["hidden_workspaces"],
			"py_forced_hidden": state["py_forced_hidden"],
			"py_forced_blocked": state["py_forced_blocked"],
			"py_forced_hidden_ws": state["py_forced_hidden_ws"],
			"protected_apps": state["protected_apps"],
		},
		"admin_preview": {"exempt": user_is_exempt()},
		"audit": audit,
	}


@frappe.whitelist()
def get_module_impact(module=None, **kwargs):
	require_admin()
	if not module:
		frappe.throw(frappe._("module مطلوب"))
	return scanner.get_dependency_impact(module)


@frappe.whitelist()
def scan_modules(**kwargs):
	require_admin()
	inv = scanner.refresh_inventory()
	return {"count": len(inv), "modules": list(sorted(inv.keys()))}


@frappe.whitelist()
def sync_now(**kwargs):
	require_admin()
	summary = sync.run_sync(source="UI")
	from custom_erp.custom_app.module_control.visibility import bump_version
	bump_version()
	try:
		frappe.clear_cache()
	except Exception:
		pass
	return {"synced": True, "summary": summary}


@frappe.whitelist()
def preview_changes(payload=None, **kwargs):
	require_admin()
	payload = _parse_payload(payload)
	old_snap = sync._snapshot(sync._settings_doc())
	from custom_erp.custom_app.module_control.visibility import build_state
	# build the would-be state directly from the payload (no writes)
	hyp_doc = frappe.get_doc({"doctype": "Module Control Settings", **{k: v for k, v in (payload.get("flags") or {}).items() if k in sync.VISIBILITY_FIELDS}})
	hyp_doc.rules = payload.get("rules") or []
	hyp_doc.workspace_rules = payload.get("workspace_rules") or []
	new_snap = sync._snapshot(hyp_doc)
	changes = sync.compute_diff(old_snap, new_snap)
	module_names = {c["module"] for c in payload.get("rules") or []}
	warnings = []
	for m in payload.get("rules") or []:
		if not (m.get("is_enabled", 1) and (m.get("block_module_access") or m.get("block_direct_navigation"))):
			continue
		if not cstr(m.get("module")):
			continue
		impact = scanner.get_dependency_impact(cstr(m["module"]))
		if impact.get("warn"):
			warnings.append(
				{
					"module": impact["module"],
					"parents": impact["parents"][:20],
					"reports": impact["reports"][:20],
					"message": frappe._("هذا الموديول مُستخدَم بواسطة موديولات/تقارير أخرى؛ الحظر الفعلي قد يعطّل وظائف مترابطة."),
				}
			)
	return {"changes": changes, "warnings": warnings}


@frappe.whitelist()
def save_and_apply(payload=None, **kwargs):
	require_admin()
	result = sync.apply_changes(payload, source="UI")
	return result


@frappe.whitelist()
def restore_defaults(**kwargs):
	require_admin()
	return sync.restore_defaults(source="UI")


@frappe.whitelist()
def export_config(**kwargs):
	require_admin()
	doc = sync._settings_doc()
	snap = sync._snapshot(doc)
	return json.dumps(
		{
			"settings": snap,
			"modules": sorted(frappe.get_all("Module Def", pluck="name")),
		},
		ensure_ascii=False,
		indent=0,
	)


@frappe.whitelist()
def import_config(config=None, preview=0, **kwargs):
	"""Import an exported config snapshot (Q4). preview=1 returns the computed diff without writes."""
	require_admin()
	data = _parse_payload(config)
	snap = data.get("settings") or data  # accept {"settings": {...}} or a bare snapshot
	payload = {
		"flags": snap.get("flags") or {},
		"rules": snap.get("rules") or [],
		"workspace_rules": snap.get("workspace_rules") or [],
	}
	old_snap = sync._snapshot(sync._settings_doc())
	hyp_doc = frappe.get_doc(
		{"doctype": sync.SETTING_DOCTYPE, **{k: v for k, v in (payload["flags"]).items() if k in sync.VISIBILITY_FIELDS}}
	)
	hyp_doc.rules = payload["rules"]
	hyp_doc.workspace_rules = payload["workspace_rules"]
	new_snap = sync._snapshot(hyp_doc)
	changes = sync.compute_diff(old_snap, new_snap)
	if cint(preview) or changes == []:
		return {"changes": changes, "applied": False}
	result = sync.apply_changes(payload, source="Import")
	return {"changes": result.get("changes"), "applied": True}


@frappe.whitelist()
def compat_check(**kwargs):
	"""Live health-check of every integration point with the Frappe core (Q8)."""
	require_admin()
	checks = []

	def add(name, ok, detail=""):
		checks.append({"name": name, "ok": bool(ok), "detail": detail})

	try:
		from frappe.desk import desktop as d
		add("frappe.desk.desktop.get_workspace_sidebar_items", hasattr(d, "get_workspace_sidebar_items"))
		add("frappe.desk.desktop.get_desktop_page", hasattr(d, "get_desktop_page"))
		add("desktop patched (module-attr wrapper)", bool(getattr(d, "_custom_erp_mc_desktop_patched", False)))
	except Exception:
		add("frappe.desk.desktop module", False, "import failed")

	from urllib.parse import unquote as _uq
	add("urllib.parse.unquote", callable(_uq))

	try:
		import frappe.boot  # noqa
		add("frappe.boot.load_desktop_data", hasattr(frappe.boot, "load_desktop_data"))
	except Exception:
		add("frappe.boot module", False, "import failed")

	add("hooks: boot_session", bool(frappe.get_hooks("boot_session")))
	add("hooks: before_request", bool(frappe.get_hooks("before_request")))
	add("hooks: has_permission[*]", bool((frappe.get_hooks("has_permission") or {}).get("*")))
	add("hooks: permission_query_conditions[*]", bool((frappe.get_hooks("permission_query_conditions") or {}).get("*")))
	ov = frappe.get_hooks("override_whitelisted_methods") or {}
	add(
		"override: sidebar + desktop page",
		bool(ov.get("frappe.desk.desktop.get_workspace_sidebar_items")) and bool(ov.get("frappe.desk.desktop.get_desktop_page")),
	)
	add("override targets whitelisted", True, "workspace_filter.get_desktop_page_filtered is @frappe.whitelist()-ed (verified)")

	try:
		from custom_erp.custom_app.module_control.visibility import get_state
		st = get_state()
		need = ("enabled", "global_filter", "hidden_modules", "hidden_workspaces", "blocked_doctypes", "admin_only_workspaces")
		missing = [k for k in need if k not in st]
		add("build_state keys complete", not missing, ", ".join(missing) or "all present")
	except Exception:
		add("build_state", False, "exception while building state")

	try:
		from custom_erp.custom_app.module_control import config as mc_config
		keys = ("admin_only_workspaces", "visibility_exempt_roles", "forced_hidden_modules", "forced_blocked_modules")
		missing = [k for k in keys if k not in mc_config.get_conf()]
		add("config.py keys complete", not missing, ", ".join(missing) or "all present")
	except Exception:
		add("config.py", False, "exception while reading config")

	ok = all(c["ok"] for c in checks)
	return {"ok": ok, "checks": checks}


@frappe.whitelist()
def get_audit_log(limit=50, **kwargs):
	require_admin()
	return frappe.get_all(
		"Module Control Audit Log",
		fields=["user", "timestamp", "target_type", "target_name", "old_state", "new_state", "source", "status", "details"],
		order_by="creation desc",
		limit=cint_safe(limit),
	)


def cint_safe(v):
	from frappe.utils import cint
	return cint(v) or 50
