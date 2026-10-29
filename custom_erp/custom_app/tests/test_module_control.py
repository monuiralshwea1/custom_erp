import frappe
import unittest

from frappe.tests.utils import FrappeTestCase

from custom_erp.custom_app.module_control import sync
from custom_erp.custom_app.module_control.visibility import get_state


def _set_payload(rules, workspace_rules=None, flags=None):
	"""Apply a test rule set without UI (direct apply_changes, source='UI-test')."""
	return sync.apply_changes(
		{"rules": rules, "workspace_rules": workspace_rules or [], "flags": flags or {}},
		source="UI-test",
	)


class TestModuleControl(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		backup = frappe.get_doc("Module Control Settings")
		cls.original_snapshot = sync._snapshot(backup)

	@classmethod
	def tearDownClass(cls):
		# restore exact pre-test snapshot (python-forced rules still re-enforced by sync)
		snap = cls.original_snapshot
		payload = {"flags": snap["flags"], "rules": snap["rules"], "workspace_rules": snap["workspace_rules"]}
		sync.apply_changes(payload, source="UI-test-restore", audit=False)
		frappe.clear_cache()

	def test_hide_module_state_effective(self):
		"""Module marked hidden must appear in state.hidden_modules (all users)."""
		rules = [{"module": "Projects", "is_enabled": 1, "hide_module": 1}]
		_set_payload(rules)
		state = get_state()
		self.assertIn("Projects", state["hidden_modules"])

	def test_workspace_rule_hide_single(self):
		"""A single workspace rule hides only that workspace name."""
		ws = frappe.db.get_value("Workspace", {"module": "Projects"}, "name")
		self.assertTrue(ws)
		_set_payload([], workspace_rules=[{"workspace": ws, "hide_workspace": 1}])
		state = get_state()
		self.assertIn(ws, state["hidden_workspaces"])
		# rest of the module is NOT hidden by a single-workspace rule

	def test_blocking_generates_doctype_list(self):
		rules = [{"module": "Projects", "is_enabled": 1, "block_module_access": 1, "block_direct_navigation": 1,
			"hide_module": 1, "hide_all_workspaces": 1, "hide_from_search": 1}]
		_set_payload(rules, flags={"enabled": 1, "enable_access_blocking": 1, "enable_global_workspace_filter": 1,
			"strict_visibility_mode": 0, "enable_audit_logging": 1, "default_behavior_for_new_modules": "Follow Config"})
		state = get_state()
		self.assertTrue(len(state["blocked_doctypes"]) > 0)
		self.assertIn("Project", state["blocked_doctypes"])
		self.assertIn("Task", state["blocked_doctypes"])

	def test_py_forced_rules_persist_after_ui_unlock_attempt(self):
		"""Python config forced rules cannot be removed by UI (enforcement)."""
		from custom_erp.custom_app.module_control import config
		conf = config.get_conf()
		if not conf["forced_hidden_modules"] and not conf["forced_blocked_modules"]:
			self.skipTest("لا توجد قواعد مفروضة من Python في config.py — الحالة الافتراضية للإنتاج")

		module = conf["forced_hidden_modules"] or conf["forced_blocked_modules"]
		module = module[0]
		rules = [{"module": module, "is_enabled": 0, "hide_module": 0} if module in conf["forced_hidden_modules"] else
			{"module": module, "is_enabled": 0, "hide_module": 0, "block_module_access": 0}]
		sync.apply_changes({"rules": rules, "workspace_rules": []}, source="UI-test", audit=False)
		state = get_state()
		if module in conf["forced_hidden_modules"]:
			self.assertIn(module, state["hidden_modules"])
		if module in conf["forced_blocked_modules"]:
			self.assertIn(module, state["blocked_modules"])

	def test_unhide_returns_module_to_visible(self):
		"""After removing the rule, hidden list is empty again (rollback semantics)."""
		rules = [{"module": "Projects", "is_enabled": 1, "hide_module": 1}]
		_set_payload(rules)
		self.assertIn("Projects", get_state()["hidden_modules"])
		# now unhide via empty rule set
		_set_payload([], flags={"enabled": 1, "enable_global_workspace_filter": 1, "enable_access_blocking": 0,
			"strict_visibility_mode": 0, "enable_audit_logging": 1, "default_behavior_for_new_modules": "Follow Config"})
		self.assertNotIn("Projects", get_state()["hidden_modules"])

	def test_disabled_rule_has_no_effect(self):
		rules = [{"module": "Projects", "is_enabled": 0, "hide_module": 1}]
		_set_payload(rules)
		state = get_state()
		self.assertNotIn("Projects", state["hidden_modules"])

	def test_admin_access_blocking_core_bypass_documented(self):
		"""
		Verify the DOCUMENTED core limitation: F.has_permission short-circuits
		user == Administrator BEFORE hooks, so access blocking never applies to
		Administrator. Visual hiding still filters Administrator's navigation.
		"""
		admin_perm = frappe.permissions.has_permission("Sales Invoice", "read", user="Administrator", raise_exception=False)
		self.assertTrue(admin_perm)

	def test_admin_only_workspace_visibility(self):
		"""Admin-only workspace (إدارة التطوير): exists (with stock private-workspace
		naming "<label>-<user>"), hidden for non-admins, visible for Administrator."""
		from custom_erp.custom_app.module_control import sync
		from custom_erp.custom_app.module_control.visibility import (
			admin_only_matches,
			get_state,
			workspace_admin_only,
		)
		created = sync.ensure_admin_only_workspaces()
		state = get_state()
		admin_wss = state.get("admin_only_workspaces") or []
		self.assertTrue(admin_wss, "config admin_only_workspaces must be non-empty for this test")
		name = admin_wss[0]
		doc = frappe.get_all("Workspace", filters={"title": name}, fields=["name", "title", "public", "for_user"], limit=1)
		self.assertTrue(doc, "workspace with the clean title must exist")
		self.assertEqual(doc[0].title, name)
		self.assertFalse(doc[0].public)
		self.assertEqual(doc[0].for_user, "Administrator")
		# doc name follows the stock Frappe private-workspace router naming
		self.assertTrue(admin_only_matches(doc[0].name, admin_wss))
		# Administrator sees it
		self.assertFalse(workspace_admin_only(name, user="Administrator"))
		self.assertFalse(workspace_admin_only(doc[0].name, user="Administrator"))
		# everyone else does not (by both the clean title and the doc name)
		self.assertTrue(workspace_admin_only(name, user="smartqa@example.com"))
		self.assertTrue(workspace_admin_only(doc[0].name, user="moneerali@gmail.com"))
		if created:
			# cleanup created-on-test workspaces
			for w in created:
				existing = frappe.get_all("Workspace", filters={"title": w}, pluck="name", limit=1)
				if existing:
					frappe.delete_doc("Workspace", existing[0], force=1)
			frappe.db.commit()

	def test_import_config_preview_no_write(self):
		"""import_config(preview=1) must return the diff WITHOUT touching settings (Q4)."""
		from custom_erp.custom_app.module_control import api, sync
		before = sync._snapshot(sync._settings_doc())
		export = api.export_config()
		res = api.import_config(config=export, preview=1)
		self.assertIn("changes", res)
		self.assertFalse(res.get("applied"))
		after = sync._snapshot(sync._settings_doc())
		self.assertEqual(before, after, "preview must not write anything")
		# importing our own current snapshot is idempotent → no changes
		self.assertEqual(res["changes"], [])

	def test_query_conditions_hook_blocks_doctype(self):
		from custom_erp.custom_app.module_control import permissions as mc_perm
		rules = [{"module": "Projects", "is_enabled": 1, "block_module_access": 1}]
		_set_payload(rules, flags={"enabled": 1, "enable_access_blocking": 1, "enable_global_workspace_filter": 1,
			"strict_visibility_mode": 0, "enable_audit_logging": 1, "default_behavior_for_new_modules": "Follow Config"})
		cond = mc_perm.query_conditions_hook(user="smartqa@example.com", doctype="Project")
		self.assertEqual(cond, "1=0")
		cond2 = mc_perm.query_conditions_hook(user="smartqa@example.com", doctype="Customer")
		self.assertIsNone(cond2)
		# list stays invisible via get_list — must run as a NON-admin session
		# (Administrator is bypassed by core, documented limitation)
		prev_user = frappe.session.user
		try:
			frappe.set_user("smartqa@example.com")
			rows = frappe.get_list("Project", limit_page_length=2)
			self.assertEqual(len(rows), 0)
		finally:
			frappe.set_user(prev_user)
