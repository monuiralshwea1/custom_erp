# -*- coding: utf-8 -*-
# Central Module Control Manager — Single settings doctype controller.
import frappe
from frappe.model.document import Document


class ModuleControlSettings(Document):
	def validate(self):
		# Capture the state as saved IN DB before this change (used for audit after save)
		try:
			if frappe.flags.get("mc_sync_running"):
				self._mc_before_snapshot = None
				return
			from custom_erp.custom_app.module_control.sync import _snapshot, _settings_doc
			old_doc = _settings_doc()
			# NOTE: cached doc may not yet reflect pending changes; fetch fresh values
			old_doc = frappe.get_doc(self.doctype) if old_doc else None
			self._mc_before_snapshot = _snapshot(old_doc) if old_doc else None
		except Exception:
			import traceback
			frappe.log_error(traceback.format_exc()[:2000], "ModuleControl validate")
			self._mc_before_snapshot = None

	def on_update(self):
		if getattr(self.flags, "mc_ignore_on_update", False):
			return
		try:
			from custom_erp.custom_app.module_control.sync import after_settings_saved
			after_settings_saved(self, source="UI", prev_snapshot=getattr(self, "_mc_before_snapshot", None))
		except Exception:
			import traceback
			frappe.log_error(traceback.format_exc()[:3000], "ModuleControl settings on_update")
