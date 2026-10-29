# -*- coding: utf-8 -*-
"""
Scanner: inventory of Module Defs, Workspaces, DocTypes/Pages/Reports counts,
and dependency impact analysis used for "Preview Impact" warnings.

All functions are read-only and use cached queries where possible.
"""
from collections import defaultdict

import frappe

IMPACT_TTL = 3600


def get_installed_apps():
	try:
		return frappe.get_installed_apps() or []
	except Exception:
		return []


def get_module_inventory():
	"""Return {module_name: {app, app_title, doctypes, pages, reports, workspaces, entities}}."""
	inventory = {}

	def _put(name, **kw):
		inv = inventory.setdefault(name, {"module": name, "app": None, "doctypes": 0, "pages": 0, "reports": 0, "workspaces": 0})
		inv.update(kw)

	for md in frappe.get_all("Module Def", fields=["name", "app_name", "module_name"]):
		_put(md.name, app=md.app_name or "", module_title=md.module_name or "")

	doctype_rows = frappe.get_all("DocType", fields=["name", "module"])
	dict_count = defaultdict(int)
	for r in doctype_rows:
		dict_count[r.module] += 1

	page_rows = frappe.get_all("Page", fields=["name", "module"])
	page_count = defaultdict(int)
	for r in page_rows:
		page_count[r.module] += 1

	report_rows = frappe.get_all("Report", fields=["name", "module", "ref_doctype"])
	report_count = defaultdict(int)
	for r in report_rows:
		report_count[r.module] += 1

	return {
		"inventory": inventory,
		"doctype_count": dict(dict_count),
		"page_count": dict(page_count),
		"report_count": dict(report_count),
	}


def refresh_inventory():
	"""Full module inventory including workspace listing and entity counts."""
	inv = get_module_inventory()
	inventory = inv["inventory"]
	for name, item in inventory.items():
		item["doctypes"] = inv["doctype_count"].get(name, 0)
		item["pages"] = inv["page_count"].get(name, 0)
		item["reports"] = inv["report_count"].get(name, 0)
		item["workspaces"] = frappe.get_all(
			"Workspace",
			filters={"module": name},
			fields=["name", "is_hidden", "public"],
		)
		item["workspace_count"] = len(item["workspaces"])
	return inventory


def get_module_workspaces(module_name):
	try:
		return frappe.get_all(
			"Workspace",
			filters={"module": module_name},
			fields=["name", "title", "is_hidden", "public", "for_user"],
			order_by="sequence_id asc, name asc",
		)
	except Exception:
		return []


def _mc_impact_cache_key(module):
	return "custom_erp:module_control:impact:{0}".format(frappe.utils.sha256_hash(frappe.utils.cstr(module)))


def get_dependency_impact(module):
	"""
	Compute dependency warnings for blocking/hiding `module`:
	lists "parents" (doctypes of OTHER modules; plus Reports elsewhere)
	that link into the target module's doctypes.
	Cached 1h per module; only computed on demand (Scan / Preview buttons).
	"""
	key = _mc_impact_cache_key(module)
	cached = frappe.cache.get_value(key)
	if cached:
		return cached

	targets = frappe.get_all("DocType", filters={"module": module}, pluck="name")
	result = {"module": module, "target_doctypes": targets, "parents": [], "reports": [], "warn": False}
	if not targets:
		result["warn"] = False
		result["note"] = "لا يوجد DocTypes في هذا الموديول؛ الحظر آمن نسبياً."
		frappe.cache.set_value(key, result, expires_in_sec=IMPACT_TTL)
		return result

	module_owner = {
		d.name: (d.module or "") for d in frappe.get_all("DocType", fields=["name", "module"])
	}

	# DocField links INTO target doctypes (options == doctype name)
	try:
		docs = frappe.get_all(
			"DocField",
			filters={"fieldtype": ("in", ["Link"]), "options": ("in", targets)},
			fields=["parent"],
			limit=1000,
		)
		parents = {d.parent for d in docs}
	except Exception:
		parents = set()

	# Custom fields may add links too
	try:
		cfd = frappe.get_all(
			"Custom Field",
			filters={"fieldtype": "Link", "options": ("in", targets)},
			fields=["dt as parent"],
			limit=500,
		)
		parents |= {d.parent for d in cfd}
	except Exception:
		pass

	# Reports referencing target doctypes from other modules
	try:
		reps = frappe.get_all(
			"Report",
			filters={"ref_doctype": ("in", targets)},
			fields=["name", "module"],
			limit=200,
		)
	except Exception:
		reps = []

	warn_parents = []
	for p in parents:
		if p in targets:
			continue
		owner = module_owner.get(p)
		if owner and owner != module:
			warn_parents.append({"doctype": p, "module": owner})

	warn_reports = [
		{"report": r.name, "module": r.module} for r in reps if r.module and r.module != module
	]
	result["parents"] = warn_parents
	result["reports"] = warn_reports
	result["warn"] = bool(warn_parents or warn_reports)
	frappe.cache.set_value(key, result, expires_in_sec=IMPACT_TTL)
	return result


def get_apps_of_modules(modules):
	"""Return {app_name: [module,...]} restricted to given module names."""
	rows = frappe.get_all("Module Def", filters={"name": ("in", modules or [])}, fields=["name", "app_name"])
	mapping = defaultdict(list)
	for r in rows:
		mapping[r.app_name or "frappe"].append(r.name)
	return dict(mapping)


def get_module_entity_list(module):
	return {
		"doctypes": frappe.get_all("DocType", filters={"module": module}, pluck="name", limit=500),
		"pages": frappe.get_all("Page", filters={"module": module}, pluck="name", limit=500),
		"reports": frappe.get_all("Report", filters={"module": module}, pluck="name", limit=500),
		"workspaces": frappe.get_all("Workspace", filters={"module": module}, pluck="name", limit=500),
	}
