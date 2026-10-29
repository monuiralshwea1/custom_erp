# -*- coding: utf-8 -*-
"""
Sync engine for Central Module Control Manager.

Responsibilities:
  - run_sync(): idempotent reconcile of Module Control Settings with
    module_control.config.py forced rules; backfills module_name; trims rules
    pointing to non-existent modules/workspaces (disable rather than delete).
  - apply_changes(): commit UI-provided rule tables, enforce python rules,
    bump data version, full cache clear, audit-log the diff.
  - restore_defaults(): remove only rules this system owns (python-enforced
    rows are re-synced, everything else dropped) and reset flag defaults.
  - setup_after_install / after_migrate / auto-sync doc events.
"""
import json

import frappe
from frappe.utils import now_datetime, cstr

SETTING_DOCTYPE = "Module Control Settings"
RECURSION_FLAG = "mc_sync_running"
AUTOSYNC_LOCK_KEY = "custom_erp:module_control:auto_sync_lock"

VISIBILITY_FIELDS = (
	"enabled",
	"enable_global_workspace_filter",
	"enable_access_blocking",
	"strict_visibility_mode",
	"enable_audit_logging",
	"default_behavior_for_new_modules",
)


ADMIN_WORKSPACE_LABEL = "إدارة التطوير"
ADMIN_USER = "Administrator"


def ensure_admin_only_workspaces(source="Sync"):
	"""Create the config-listed admin-only workspaces (e.g. إدارة التطوير) if missing.

	Created PRIVATE (public=0, for_user=Administrator) so the core already hides
	them from other users; workspace_filter/visibility additionally enforce the
	admin-only rule even if someone flips the public flag back on.

	Naming matches the stock Frappe client router for private workspaces:
	name/label = "<title>-<user>" (as the Workspace UI does in workspace.js),
	while the displayed `title` stays the clean configured label."""
	from custom_erp.custom_app.module_control import config as mc_config

	names = mc_config.get_conf().get("admin_only_workspaces") or []
	created = []
	migrated = []
	for cfg_label in names:
		doc_name = "{}-{}".format(cfg_label, ADMIN_USER)
		if frappe.get_all("Workspace", filters={"name": doc_name}, limit=1):
			continue
		# legacy shape created before the router-naming fix (name == label):
		# rename in place so shortcuts/links children are preserved
		legacy = frappe.get_all("Workspace", filters={"label": cfg_label}, pluck="name", limit=1)
		if legacy and legacy[0] != doc_name:
			frappe.rename_doc("Workspace", legacy[0], doc_name, force=True)
			frappe.db.set_value("Workspace", doc_name, "label", doc_name)
			frappe.db.set_value("Workspace", doc_name, "title", cfg_label)
			migrated.append(cfg_label)
			continue
		if frappe.get_all("Workspace", filters={"name": cfg_label}, limit=1):
			continue
		module_of_app = "custom app"
		module = module_of_app if frappe.db.exists("Module Def", module_of_app) else None

		shortcuts = [
			{"label": "⚙️ لوحة التحكم في الموديولات", "type": "URL", "url": "/app/module-control-settings", "color": "blue"},
			{"label": "🧾 سجل التدقيق", "type": "DocType", "link_to": "Module Control Audit Log", "color": "purple"},
			{"label": "🧩 الموديولات", "type": "DocType", "link_to": "Module Def", "color": "green"},
			{"label": "🗂️ المساحات", "type": "DocType", "link_to": "Workspace", "color": "cyan"},
			{"label": "🧱 قواعد المساحات", "type": "DocType", "link_to": "Workspace Control Rule", "color": "orange"},
			{"label": "📄 أنماط الصفحات", "type": "DocType", "link_to": "Page", "color": "gray"},
		]
		content = [
			{"id": "mc-dev-header", "type": "header", "data": {"col": 12, "text": "<b>🛠️ إدارة التطوير — مركز التحكم في الموديولات والتخصيصات (للمسؤول فقط)</b>"}},
			{"id": "mc-dev-sp-1", "type": "spacer", "data": {"col": 12}},
		]
		for i, sc in enumerate(shortcuts):
			content.append({"id": "mc-dev-sh-%d" % i, "type": "shortcut", "data": {"shortcut_name": sc["label"], "col": 3}})
		content.append({"id": "mc-dev-sp-links", "type": "card", "data": {"card_name": "التحكم في الموديولات", "col": 4}})

		doc = frappe.get_doc(
			{
				"doctype": "Workspace",
				"label": doc_name,
				"title": cfg_label,
				"public": 0,
				"for_user": ADMIN_USER,
				"module": module,
				"parent_page": "",
				"content": json.dumps(content, ensure_ascii=False, indent=0),
				"shortcuts": shortcuts,
				"links": [
					{"type": "Card Break", "label": "التحكم في الموديولات"},
					{"type": "Link", "label": "Module Control Settings", "link_type": "DocType", "link_to": "Module Control Settings", "icon": "⚙️"},
					{"type": "Link", "label": "Module Control Audit Log", "link_type": "DocType", "link_to": "Module Control Audit Log", "icon": "🧾"},
					{"type": "Link", "label": "Module Def", "link_type": "DocType", "link_to": "Module Def", "icon": "🧩"},
					{"type": "Link", "label": "Workspace", "link_type": "DocType", "link_to": "Workspace", "icon": "🗂️"},
					{"type": "Link", "label": "Workspace Control Rule", "link_type": "DocType", "link_to": "Workspace Control Rule", "icon": "🧱"},
				],
			}
		)
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True)
		created.append(cfg_label)
		frappe.db.commit()
	if created or migrated:
		try:
			from custom_erp.custom_app.module_control.audit import log
			log(source, "Workspace", " / ".join(created + migrated), "", "أنشئت/رحّلت مساحة إدارة التطوير (admin-only)")
		except Exception:
			pass
	return created + migrated


def _settings_doc(for_update=False):
	if frappe.db.exists(SETTING_DOCTYPE, SETTING_DOCTYPE):
		if for_update:
			return frappe.get_doc(SETTING_DOCTYPE, SETTING_DOCTYPE)
		return frappe.get_cached_doc(SETTING_DOCTYPE, SETTING_DOCTYPE)
	return None


def _ensure_settings_exists():
	if frappe.db.exists(SETTING_DOCTYPE, SETTING_DOCTYPE):
		return False
	doc = frappe.get_doc(
		{
			"doctype": SETTING_DOCTYPE,
			"enabled": 1,
			"enable_global_workspace_filter": 0,
			"enable_access_blocking": 0,
			"strict_visibility_mode": 0,
			"enable_audit_logging": 1,
			"default_behavior_for_new_modules": "Follow Config",
			"configuration_version": 1,
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return True


def run_sync(source="Migration"):
	"""Idempotent sync of rules with python config. Returns summary dict."""
	_ensure_settings_exists()
	try:
		created_ws = ensure_admin_only_workspaces(source=source)
		if created_ws:
			from custom_erp.custom_app.module_control.visibility import bump_version as _bump
			_bump()
			try:
				frappe.clear_cache()
			except Exception:
				pass
	except Exception:
		frappe.log_error(frappe.utils.get_traceback()[:2000], "ModuleControl admin workspace ensure")
	doc = _settings_doc(for_update=True)
	from custom_erp.custom_app.module_control import config as mc_config

	conf = mc_config.get_conf()
	changed = False
	summary = {"enforced_flags": 0, "disabled_invalid": 0, "created_rules": []}

	# first-time initialization (idempotent: only when never synchronized)
	if doc.get("last_synchronization") is None or doc.get("default_behavior_for_new_modules") is None:
		doc.enabled = 1
		doc.enable_global_workspace_filter = 0
		doc.enable_access_blocking = 0
		doc.strict_visibility_mode = 0
		doc.enable_audit_logging = 1
		doc.default_behavior_for_new_modules = "Follow Config"
		changed = True
		summary["initialized_defaults"] = True

	existing_modules = set(frappe.get_all("Module Def", pluck="name"))
	existing_ws = set(frappe.get_all("Workspace", pluck="name"))

	def _find_rule(module):
		for r in doc.get("rules") or []:
			if cstr(r.module) == cstr(module):
				return r
		return None

	# 1) enforce python hidden modules
	for module in conf["forced_hidden_modules"]:
		if module not in existing_modules:
			continue
		r = _find_rule(module)
		if not r:
			r = doc.append("rules", {}) if hasattr(doc, "append") else None
			r = doc.get("rules")[-1]
			r.module = module
			summary["created_rules"].append(module)
			changed = True
		r.is_enabled = 1
		r.hide_module = 1
		r.hide_from_search = 1
		r.hide_all_workspaces = 1
		r.enforced_by = conf["enforced_by"]
		r.module_name = module
		summary["enforced_flags"] += 1
		changed = True

	# 2) enforce python blocked modules
	for module in conf["forced_blocked_modules"]:
		if module not in existing_modules:
			continue
		r = _find_rule(module)
		if not r:
			doc.append("rules", {})
			r = doc.get("rules")[-1]
			r.module = module
			summary["created_rules"].append(module)
			changed = True
		r.is_enabled = 1
		r.block_module_access = 1
		r.block_direct_navigation = 1
		r.enforced_by = conf["enforced_by"]
		r.module_name = module
		r.hide_module = r.hide_module or 0
		summary["enforced_flags"] += 1
		changed = True

	# 3) enforce python hidden workspaces (rule rows in workspace_rules)
	def _find_ws_rule(name):
		for r in doc.get("workspace_rules") or []:
			if cstr(r.workspace) == cstr(name):
				return r
		return None

	for ws in conf["forced_hidden_workspaces"]:
		if ws not in existing_ws:
			continue
		r = _find_ws_rule(ws)
		if not r:
			doc.append("workspace_rules", {})
			r = doc.get("workspace_rules")[-1]
			r.workspace = ws
			try:
				r.module = frappe.db.get_value("Workspace", ws, "module") or ""
			except Exception:
				r.module = ""
			summary["created_rules"].append(ws)
			changed = True
		r.is_enabled = 1
		r.hide_workspace = 1
		r.block_direct_navigation = 1
		r.enforced_by = conf["enforced_by"]
		r.module = frappe.db.get_value("Workspace", ws, "module") or r.module
		summary["enforced_flags"] += 1
		changed = True

	# 4) hygiene: module_name backfill + disable rules that lost their target
	for r in doc.get("rules") or []:
		if r.module and cstr(r.module) not in existing_modules:
			if r.is_enabled:
				r.is_enabled = 0
				summary["disabled_invalid"] += 1
				changed = True
			continue
		if cstr(r.module_name) != cstr(r.module) and r.module:
			r.module_name = r.module
			changed = True
	# un-enforce python rules that are no longer forced in config (config is authority)
	for r in doc.get("rules") or []:
		tag = cstr(r.enforced_by) or ""
		if tag:
			val_module = cstr(r.module)
			if val_module in conf["forced_hidden_modules"]:
				r.hide_module = 1
				r.is_enabled = 1
			elif val_module in conf["forced_blocked_modules"]:
				r.block_module_access = 1
				r.is_enabled = 1
			else:
				# no longer python-enforced → release to UI control
				r.enforced_by = ""
				changed = True

	for r in doc.get("workspace_rules") or []:
		val = cstr(r.workspace)
		if val not in existing_ws:
			if r.is_enabled:
				r.is_enabled = 0
				summary["disabled_invalid"] += 1
				changed = True
			continue
		if cstr(r.enforced_by):
			if val in conf["forced_hidden_workspaces"]:
				r.hide_workspace = 1
				r.is_enabled = 1
			else:
				r.enforced_by = ""
				changed = True
		if not cstr(r.module) and val:
			r.module = frappe.db.get_value("Workspace", val, "module") or ""

	if changed or doc.get("last_synchronization") is None:
		doc.last_synchronization = now_datetime()
		doc.flags.mc_ignore_on_update = True
		doc.flags.ignore_sync_now = True
		doc.save(ignore_permissions=True)
		frappe.db.commit()

	return summary


def after_settings_saved(doc, source="UI", prev_snapshot=None):
	"""Called from Settings DocType.on_update. Re-sync enforcement + bump version + clear caches + audit."""
	from custom_erp.custom_app.module_control.audit import log

	if frappe.flags.get(RECURSION_FLAG) or getattr(doc.flags, "mc_ignore_on_update", False):
		return
	try:
		frappe.flags[RECURSION_FLAG] = True
		run_sync(source=source)
		from custom_erp.custom_app.module_control.visibility import bump_version
		bump_version()
		try:
			frappe.clear_cache()
		except Exception:
			pass
		try:
			from custom_erp.custom_app.module_control.sync import compute_diff, _snapshot
			new_snap = _snapshot(_settings_doc())
			if prev_snapshot:
				for c in compute_diff(prev_snapshot, new_snap):
					log(source, c["type"], c["target"], c["old"], c["new"])
		except Exception:
			import traceback
			frappe.log_error(traceback.format_exc()[:2000], "ModuleControl audit diff")
	finally:
		frappe.flags.pop(RECURSION_FLAG, None)


# ------------------------------------------------------------------ apply/preview

def _parse_payload(payload):
	if isinstance(payload, str):
		payload = json.loads(payload) if payload.strip() else {}
	if not isinstance(payload, dict):
		frappe.throw("Invalid payload")
	return payload


def _snapshot(doc):
	def rule_row(r):
		return {
			"module": cstr(r.get("module") if isinstance(r, dict) else r.module),
			"is_enabled": bool(r.get("is_enabled") if isinstance(r, dict) else r.is_enabled),
			"hide_module": bool(r.get("hide_module") if isinstance(r, dict) else r.hide_module),
			"block_module_access": bool(r.get("block_module_access") if isinstance(r, dict) else r.block_module_access),
			"hide_all_workspaces": bool(r.get("hide_all_workspaces") if isinstance(r, dict) else r.hide_all_workspaces),
			"hide_from_search": bool(r.get("hide_from_search") if isinstance(r, dict) else r.hide_from_search),
			"block_direct_navigation": bool(r.get("block_direct_navigation") if isinstance(r, dict) else r.block_direct_navigation),
			"block_protected_apis": bool(r.get("block_protected_apis") if isinstance(r, dict) else r.block_protected_apis),
		}
	return {
		"flags": {k: (doc.get(k) if doc else None) for k in VISIBILITY_FIELDS},
		"rules": [rule_row(r) for r in ((doc.get("rules") or []) if doc else [])],
		"workspace_rules": [
			{
				"workspace": cstr(r.workspace if hasattr(r, "workspace") else r.get("workspace")),
				"hide": bool(r.hide_workspace if hasattr(r, "hide_workspace") else r.get("hide_workspace")),
				"block_nav": bool(r.block_direct_navigation if hasattr(r, "block_direct_navigation") else r.get("block_direct_navigation")),
			}
			for r in ((doc.get("workspace_rules") or []) if doc else [])
		],
	}


def compute_diff(old_snap, new_snap):
	changes = []
	low, lhigh = old_snap["flags"], new_snap["flags"]
	labels = {
		"enabled": "تفعيل النظام",
		"enable_global_workspace_filter": "التصفية العامة للمساحات",
		"enable_access_blocking": "حظر الوصول",
		"strict_visibility_mode": "الوضع الصارم",
		"enable_audit_logging": "سجل التدقيق",
		"default_behavior_for_new_modules": "سلوك الموديولات الجديدة",
	}
	for k, lab in labels.items():
		if lhigh.get(k) is None:
			continue  # flag not part of this change request → don't consider a change
		if low.get(k) != lhigh.get(k):
			changes.append({"type": "Setting", "target": lab, "old": cstr(low.get(k)), "new": cstr(lhigh.get(k))})

	old_rules = {r["module"]: r for r in old_snap["rules"]}
	new_rules = {r["module"]: r for r in new_snap["rules"]}
	fl = [
		"hide_module", "block_module_access", "hide_all_workspaces",
		"hide_from_search", "block_direct_navigation", "block_protected_apis",
	]
	armap = {
		"hide_module": "إخفاء الموديول",
		"block_module_access": "حظر الوصول",
		"hide_all_workspaces": "إخفاء كل المساحات",
		"hide_from_search": "إخفاء من البحث",
		"block_direct_navigation": "منع الوصول المباشر",
		"block_protected_apis": "حظر APIs المحمية",
	}
	for m in sorted(set(old_rules) | set(new_rules)):
		o, n = old_rules.get(m), new_rules.get(m)
		if not n:
			if o and o["is_enabled"]:
				changes.append({"type": "Module", "target": m, "old": "قاعدة مفعلة", "new": "أزيلت"})
			continue
		if not o:
			if n["is_enabled"]:
				changes.append({"type": "Module", "target": m, "old": "بدون قاعدة", "new": "قاعدة جديدة مفعلة"})
			continue
		for f in fl:
			if o.get(f) != n.get(f):
				changes.append({"type": "Module", "target": "{0} — {1}".format(m, armap[f]), "old": bool(o.get(f)), "new": bool(n.get(f))})
		o_on, n_on = o.get("is_enabled"), n.get("is_enabled")
		if o_on != n_on:
			changes.append({"type": "Module", "target": "{0} — التفعيل".format(m), "old": bool(o_on), "new": bool(n_on)})

	old_ws = {r["workspace"]: r for r in old_snap["workspace_rules"]}
	new_ws = {r["workspace"]: r for r in new_snap["workspace_rules"]}
	for w in sorted(set(old_ws) | set(new_ws)):
		o, n = old_ws.get(w), new_ws.get(w)
		def _s(x):
			if not x:
				return "بدون قاعدة"
			parts = []
			if x["hide"]: parts.append("إخفاء")
			if x["block_nav"]: parts.append("منع تنقل")
			return "+".join(parts) or "غير مفعلة"
		if _s(o) != _s(n):
			changes.append({"type": "Workspace", "target": w, "old": _s(o), "new": _s(n)})
	return changes


def apply_changes(payload, source="UI", bump=True, audit=True):
	"""Commit new rules + flags, enforce python config, bump version, clear caches."""
	from custom_erp.custom_app.module_control.audit import log
	from custom_erp.custom_app.module_control.visibility import bump_version

	payload = _parse_payload(payload)
	doc = _settings_doc(for_update=True)
	old_snap = _snapshot(doc)

	new_flags = payload.get("flags") or {}
	for k in VISIBILITY_FIELDS:
		if k in new_flags and new_flags[k] is not None:
			doc.set(k, new_flags[k])

	doc.set("rules", [])
	doc.set("workspace_rules", [])
	existing_modules = set(frappe.get_all("Module Def", pluck="name"))
	existing_ws = set(frappe.get_all("Workspace", pluck="name"))
	for r in payload.get("rules") or []:
		m = cstr(r.get("module")).strip()
		if not m or m not in existing_modules:
			continue
		doc.append("rules", {
			"module": m,
			"module_name": m,
			"is_enabled": 1 if r.get("is_enabled", 1) else 0,
			"hide_module": 1 if r.get("hide_module") else 0,
			"block_module_access": 1 if r.get("block_module_access") else 0,
			"hide_all_workspaces": 1 if r.get("hide_all_workspaces") else 0,
			"hide_from_search": 1 if r.get("hide_from_search") else 0,
			"block_direct_navigation": 1 if r.get("block_direct_navigation") else 0,
			"block_protected_apis": 1 if r.get("block_protected_apis") else 0,
			"enforced_by": (r.get("enforced_by") or "").strip(),
			"description": r.get("description") or "",
		})
	for r in payload.get("workspace_rules") or []:
		w = cstr(r.get("workspace")).strip()
		if not w or w not in existing_ws:
			continue
		doc.append("workspace_rules", {
			"workspace": w,
			"module": frappe.db.get_value("Workspace", w, "module") or cstr(r.get("module") or ""),
			"hide_workspace": 1 if r.get("hide_workspace") or r.get("hide") else 0,
			"block_direct_navigation": 1 if r.get("block_direct_navigation") or r.get("block_nav") else 0,
			"is_enabled": 1 if r.get("is_enabled", 1) else 0,
			"description": r.get("description") or "",
		})

	doc.flags.mc_ignore_on_update = True
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	# re-enforce python rules over whatever the UI sent
	run_sync(source=source)
	if bump:
		bump_version()
	try:
		frappe.clear_cache()
	except Exception:
		pass

	doc2 = _settings_doc()
	new_snap = _snapshot(doc2)
	changes = compute_diff(old_snap, new_snap)
	if audit:
		for c in changes:
			log(
				source,
				c["type"],
				c["target"],
				cstr(c["old"]),
				cstr(c["new"]),
			)
	return {"applied": True, "changes": changes}


def restore_defaults(source="UI"):
	"""Roll back everything this system owns. Keeps python-enforced rules (config is authority)."""
	from custom_erp.custom_app.module_control.visibility import bump_version
	doc = _settings_doc(for_update=True)
	old_snap = _snapshot(doc)

	doc.enabled = 1
	doc.enable_global_workspace_filter = 1
	doc.enable_access_blocking = 0
	doc.strict_visibility_mode = 0
	doc.enable_audit_logging = 1
	doc.default_behavior_for_new_modules = "Follow Config"
	doc.known_modules_baseline = ""

	doc.set("rules", [])
	doc.set("workspace_rules", [])
	doc.flags.mc_ignore_on_update = True
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	run_sync(source=source)  # re-add python-forced rows
	bump_version()
	try:
		frappe.clear_cache()
	except Exception:
		pass
	new_snap = _snapshot(_settings_doc())
	return {"restored": True, "changes": compute_diff(old_snap, new_snap)}


# ------------------------------------------------------- auto-sync triggers

def _autosync_queue():
	lock = frappe.cache.get_value(AUTOSYNC_LOCK_KEY)
	if lock:
		return
	try:
		frappe.cache.set_value(AUTOSYNC_LOCK_KEY, 1, expires_in_sec=60)
	except Exception:
		pass
	frappe.enqueue(
		"custom_erp.custom_app.module_control.sync.auto_sync_task",
		queue="short",
		timeout=600,
	)


def on_module_changed(doc, event=None):
	if frappe.flags.get(RECURSION_FLAG) or frappe.flags.get("in_install") or frappe.flags.get("in_migrate"):
		return
	settings = _settings_doc()
	if not settings or not settings.enabled:
		return
	_autosync_queue()


def on_workspace_changed(doc, event=None):
	if frappe.flags.get(RECURSION_FLAG) or frappe.flags.get("in_install") or frappe.flags.get("in_migrate"):
		return
	settings = _settings_doc()
	if not settings or not settings.enabled:
		return
	_autosync_queue()


def auto_sync_task(*args, **kwargs):
	try:
		summary = run_sync(source="Auto - Triggered")
		# new things may exist → new data version so desks refresh
		from custom_erp.custom_app.module_control.visibility import bump_version
		bump_version()
		return summary
	except Exception:
		frappe.log_error(frappe.utils.get_traceback()[:2000], "ModuleControl AutoSync")
		return None


def after_migrate(*args, **kwargs):
	try:
		if frappe.flags.get("in_migrate") or not frappe.db:
			return
		summary = run_sync(source="Migration")
		print("MODULE-CONTROL-SYNC:", summary)
	except Exception:
		frappe.log_error(frappe.utils.get_traceback()[:2000], "ModuleControl after_migrate")


def setup_after_install(*args, **kwargs):
	try:
		_ensure_settings_exists()
		run_sync(source="Install")
	except Exception:
		frappe.log_error(frappe.utils.get_traceback()[:2000], "ModuleControl after_install")
