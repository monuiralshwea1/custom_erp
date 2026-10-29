# -*- coding: utf-8 -*-
"""
Central runtime state for Central Module Control Manager.

build_state() merges (by priority):
  1. Python config强制 rules  (module_control.config)
  2. Module Control Settings rules
  3. Hidden-By-Default behaviour for newly discovered modules

The built state is cached in redis (site-scoped, user-INDEPENDENT) with a TTL,
and versioned by the settings' configuration_version so Apply always produces
a fresh version key (no stale cache, no per-user leaks).
"""
import frappe
from frappe.utils import cint, cstr

from custom_erp.custom_app.module_control import config as mc_config

STATE_TTL = 1800
VERSION_CACHE_KEY = "custom_erp:module_control:data_version"

# Doctypes that must never be blanket-blocked (system/admin operational doctypes,
# plus the controller/managers of this system itself).
EXCLUDED_DOCTYPES = {
	"Module Control Settings",
	"Module Control Rule",
	"Workspace Control Rule",
	"Module Control Audit Log",
	"User",
	"Role",
	"Role Profile",
	"User Permission",
	"DocType",
	"Module Def",
	"Page",
	"Report",
	"Workspace",
	"DocField",
	"Custom Field",
	"Property Setter",
	"Client Script",
	"Server Script",
	"Onboarding",
	"Onboarding Step",
	"Workspace Link",
	"Workspace Shortcut",
	"Number Card",
	"Dashboard",
	"File",
	"DocShare",
}


def _sset(name):
	return {cstr(x).strip() for x in (name or []) if cstr(x).strip()}


def get_version():
	"""Data version counter (redis-first, fall back to settings field).
	Incremented on every real change to rules/config; used to key the state cache."""
	try:
		v = frappe.cache.get_value(VERSION_CACHE_KEY)
		if v:
			return cint(v)
		v = cint(frappe.db.get_single_value("Module Control Settings", "configuration_version")) or 1
		frappe.cache.set_value(VERSION_CACHE_KEY, v, expires_in_sec=0)
		return v
	except Exception:
		return 1


def bump_version():
	try:
		v = cint(frappe.cache.get_value(VERSION_CACHE_KEY)) or cint(
			frappe.db.get_single_value("Module Control Settings", "configuration_version")
		) or 0
		nv = v + 1
		frappe.cache.set_value(VERSION_CACHE_KEY, nv, expires_in_sec=0)
		try:
			frappe.db.set_value("Module Control Settings", "Module Control Settings", "configuration_version", nv, update_modified=False)
			frappe.db.commit()
		except Exception:
			pass
		return nv
	except Exception:
		return get_version()


def build_state():
	"""Merge all rule sources into one state dict (sets serialized as sorted lists)."""
	conf = mc_config.get_conf()
	try:
		s = frappe.get_cached_doc("Module Control Settings")
	except Exception:
		s = None

	def sval(k, default=None):
		if s is None:
			return default
		v = s.get(k)
		if v is None:
			return default
		return v

	enabled = True
	if conf["enabled"] is False:
		enabled = False
	elif conf["enabled"] is None:
		enabled = bool(sval("enabled", 0))
	if s is None:
		enabled = False

	global_filter = conf["global_visibility"]
	if global_filter is None:
		global_filter = bool(sval("enable_global_workspace_filter", 0))

	access_blocking = conf["access_blocking"]
	if access_blocking is None:
		access_blocking = bool(sval("enable_access_blocking", 0))

	strict = bool(sval("strict_visibility_mode", 0))
	default_behavior = sval("default_behavior_for_new_modules") or "Follow Config"

	hidden_modules = set(mc_config.MODULE_CONTROL.get("forced_hidden_modules") or [])
	forced_hidden_modules = set(hidden_modules)
	forced_hidden_workspaces = set(mc_config.MODULE_CONTROL.get("forced_hidden_workspaces") or [])
	forced_blocked_modules = set(mc_config.MODULE_CONTROL.get("forced_blocked_modules") or [])
	admin_only_workspaces = set(mc_config.MODULE_CONTROL.get("admin_only_workspaces") or [])
	visibility_exempt_roles = set(mc_config.MODULE_CONTROL.get("visibility_exempt_roles") or [])

	search_hidden_modules = set()
	blocked_modules = set(conf["forced_blocked_modules"] or [])

	hidden_workspaces = set()
	block_direct_nav_workspaces = set()

	workspace_rules = []
	for r in (s.get("workspace_rules") or []) if s else []:
		if r.get("is_enabled"):
			row = {
				"workspace": cstr(r.workspace),
				"module": cstr(r.module),
				"hide": bool(r.hide_workspace),
				"block_nav": bool(r.block_direct_navigation),
				"enforced": bool(r.enforced_by),
			}
			if row["workspace"]:
				workspace_rules.append(row)
				if row["hide"]:
					hidden_workspaces.add(row["workspace"])
				if row["block_nav"]:
					block_direct_nav_workspaces.add(row["workspace"])

	module_rules = {}
	for r in (s.get("rules") or []) if s else []:
		if not r.get("module"):
			continue
		enforced = (cstr(r.enforced_by) or "").strip()
		py_forced = cstr(r.module) in forced_hidden_modules
		d = {
			"module": cstr(r.module),
			"is_enabled": bool(r.is_enabled),
			"hide_module": bool(r.hide_module),
			"block_module_access": bool(r.block_module_access),
			"hide_all_workspaces": bool(r.hide_all_workspaces),
			"hide_from_search": bool(r.hide_from_search),
			"block_direct_navigation": bool(r.block_direct_navigation),
			"block_protected_apis": bool(r.block_protected_apis),
			"enforced_by": cstr(r.enforced_by),
			"py_forced": py_forced,
		}
		module_rules[d["module"]] = d
		if not d["is_enabled"]:
			continue
		if d["hide_module"]:
			hidden_modules.add(d["module"])
			# enforced python rules must always hide (UI cannot un-hide)
			if py_forced:
				d["hide_module"] = True
				d["is_enabled"] = True
		if d["hide_module"] or d["hide_from_search"]:
			search_hidden_modules.add(d["module"])
		if d["block_module_access"] or d["block_direct_navigation"]:
			blocked_modules.add(d["module"])

	all_hidden_workspaces = forced_hidden_workspaces | hidden_workspaces
	block_direct_nav_workspaces |= set(forced_hidden_workspaces)

	# hide_all_workspaces: resolve module → workspace names (recomputed each state build,
	# so workspaces created later are picked up automatically after the next cache refresh)
	hide_all = [m for m, d in module_rules.items() if d["is_enabled"] and d["hide_all_workspaces"]]
	if hide_all or all_hidden_workspaces or hidden_modules or blocked_modules:
		ws_rows = frappe.get_all("Workspace", fields=["name", "module"], limit=5000)
		module_of_ws = {cstr(w.name): cstr(w.module) for w in ws_rows}
		for wname, wmodule in module_of_ws.items():
			if wmodule in hide_all:
				all_hidden_workspaces.add(wname)
			if wmodule in blocked_modules or wmodule in hidden_modules:
				all_hidden_workspaces.add(wname)
				block_direct_nav_workspaces.add(wname)
	else:
		module_of_ws = {}

	# Blocked by default behaviour for NEW modules
	if default_behavior == "Hidden By Default" and enabled:
		baseline = _sset(
			(frappe.db.get_single_value("Module Control Settings", "known_modules_baseline") or "").split(",")
			if frappe.db.get_single_value("Module Control Settings", "known_modules_baseline")
			else []
		)
		try:
			current_modules = set(
				x["module"] for x in frappe.get_all("Module Def", fields=["name as module"], limit=5000)
			)
			current_modules = {cstr(x) for x in current_modules}
		except Exception:
			current_modules = set()
		if baseline:
			hidden_modules |= (current_modules - baseline)
			blocked_modules |= (current_modules - baseline)
		else:
			baseline = current_modules
			frappe.db.set_value("Module Control Settings", "Module Control Settings", "known_modules_baseline", ",".join(sorted(baseline)), update_modified=False)

	# Basic snapshot of blocked module entities for the permission/user-control layers
	blocked_doctypes = set()
	blocked_pages = set()
	blocked_reports = set()
	page_owner = {}
	report_owner = {}
	if blocked_modules:
		rows = frappe.get_all("DocType", filters={"module": ("in", sorted(blocked_modules))}, fields=["name", "module"], limit=5000)
		for r in rows:
			if r.name in EXCLUDED_DOCTYPES:
				continue
			blocked_doctypes.add(cstr(r.name))
		prows = frappe.get_all("Page", filters={"module": ("in", sorted(blocked_modules))}, fields=["name", "module"], limit=5000)
		for r in prows:
			blocked_pages.add(cstr(r.name))
			page_owner[cstr(r.name)] = cstr(r.module)
		rrows = frappe.get_all("Report", filters={"module": ("in", sorted(blocked_modules))}, fields=["name", "module"], limit=5000)
		for r in rrows:
			blocked_reports.add(cstr(r.name))
			report_owner[cstr(r.name)] = cstr(r.module)

	# Apps that own blocked modules → used for /api/method/{app}.* blocking.
	# Per-rule opt-in: the app-level method path is only blocked when the rule
	# explicitly sets block_protected_apis (python-forced blocked modules always are).
	protected_apps = set()
	mc_protected = set(conf["forced_blocked_modules"] or [])
	for _m, _d in module_rules.items():
		if _d["is_enabled"] and _d["block_module_access"] and _d["block_protected_apis"]:
			mc_protected.add(_m)
	if conf["protected_api_scope"] == "app" and mc_protected:
		try:
			mrows = frappe.get_all("Module Def", filters={"name": ("in", sorted(mc_protected))}, fields=["name", "app_name"], limit=500)
			for r in mrows:
				if (r.app_name or "").strip():
					protected_apps.add(r.app_name.strip())
		except Exception:
			pass

	state = {
		"enabled": enabled,
		"global_filter": bool(global_filter),
		"access_blocking": bool(access_blocking),
		"strict": strict,
		"apply_admin": bool(conf["apply_to_administrator"]),
		"apply_wm": bool(conf["apply_to_workspace_manager"]),
		"apply_sm": bool(conf["apply_to_system_manager"]),
		"protected_api_scope": conf["protected_api_scope"],
		"hidden_modules": sorted(hidden_modules),
		"search_hidden_modules": sorted(search_hidden_modules),
		"blocked_modules": sorted(blocked_modules),
		"blocked_doctypes": sorted(blocked_doctypes),
		"blocked_pages": sorted(blocked_pages),
		"blocked_reports": sorted(blocked_reports),
		"page_owner": page_owner,
		"report_owner": report_owner,
		"hidden_workspaces": sorted(all_hidden_workspaces),
		"block_nav_workspaces": sorted(block_direct_nav_workspaces),
		"protected_apps": sorted(protected_apps),
		"admin_only_workspaces": sorted(admin_only_workspaces),
		"visibility_exempt_roles": sorted(visibility_exempt_roles),
		"py_forced_hidden": sorted(forced_hidden_modules),
		"py_forced_hidden_ws": sorted(forced_hidden_workspaces),
		"py_forced_blocked": sorted(forced_blocked_modules),
		"workspace_rules": workspace_rules,
		"module_rules": module_rules,
		"enforced_by": conf["enforced_by"],
		"default_behavior": default_behavior,
	}
	return state


def get_state():
	"""Cache-aware state getter. Keyed by data version → survives any Apply."""
	version = get_version()
	key = "custom_erp:module_control:state:d{0}".format(version)
	try:
		cached = frappe.cache.get_value(key)
		if cached:
			return cached
	except Exception:
		pass
	try:
		state = build_state()
		try:
			frappe.cache.set_value(key, state, expires_in_sec=STATE_TTL)
		except Exception:
			pass
		return state
	except Exception:
		# very defensive: visibility filtering must never take the desk down
		frappe.logger("module_control").error(frappe.utils.get_traceback()[:3000])
		return {"enabled": False}


__all_exports__ = [
	"get_state",
	"get_version",
	"bump_version",
	"build_state",
]

# Convenience accessors used by other layers -------------------------------

def user_is_exempt(user=None):
	"""Should visual filtering be skipped for this user according to config flags?"""
	user = user or frappe.session.user
	try:
		roles = set(frappe.get_roles(user))
	except Exception:
		roles = set()
	state = get_state()
	if user == "Administrator":
		return not state["apply_admin"]
	if "Workspace Manager" in roles:
		return not state["apply_wm"]
	if "System Manager" in roles:
		return not state["apply_sm"]
	exempt_roles = set(state.get("visibility_exempt_roles") or [])
	if roles & exempt_roles:
		return True
	return False


def module_hidden(module, user=None):
	state = get_state()
	if not state["enabled"]:
		return False
	if state["strict"] or not user_is_exempt(user):
		return cstr(module) in state["hidden_modules"]
	return False


def module_search_hidden(module, user=None):
	state = get_state()
	if not state["enabled"]:
		return False
	if state["strict"] or not user_is_exempt(user):
		return cstr(module) in state["search_hidden_modules"]
	return False


def workspace_hidden(name, user=None):
	state = get_state()
	if not state["enabled"]:
		return False
	if state["strict"] or not user_is_exempt(user):
		return cstr(name) in state["hidden_workspaces"]
	return False


def workspace_admin_only(name, user=None):
	"""True when this workspace is admin-only AND the given user is NOT Administrator.

	Applies regardless of apply_to_* flags or strict mode: by design these
	workspaces are invisible to every non-admin user no matter what."""
	state = get_state()
	if not state.get("enabled"):
		return False
	if not admin_only_matches(name, state.get("admin_only_workspaces") or []):
		return False
	user = user or frappe.session.user
	return user != "Administrator"


ADMIN_USER = "Administrator"


def admin_only_matches(name, admin_names):
	"""True when `name` refers to an admin-only workspace.

	Accepts BOTH the clean configured label (e.g. «إدارة التطوير», used as
	doc title) AND the stock Frappe client-router naming for private
	workspaces: "<label>-<user>" (e.g. «إدارة التطوير-Administrator»).
	Matches, case-insensitively, the same suffix shape the Workspace UI
	creates (workspace.js: name/label = `${title}-${user}`)."""
	n = cstr(name)
	for a in (admin_names or []):
		a = cstr(a)
		if n == a:
			return True
		for suffix in ("-" + ADMIN_USER, "-" + ADMIN_USER.lower()):
			if n == a + suffix or n.lower() == (a + suffix).lower():
				return True
	return False


def doctype_blocked(doctype, user=None):
	state = get_state()
	if not state["enabled"] or not state["access_blocking"]:
		return False
	if cstr(doctype) in EXCLUDED_DOCTYPES:
		return False
	return cstr(doctype) in state["blocked_doctypes"]
