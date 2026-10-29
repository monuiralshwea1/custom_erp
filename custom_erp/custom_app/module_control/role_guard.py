# ============================================================================
# Role Guard — منع إسناد أدوار معيّنة للمستخدمين
# (جزء Central Module Control Manager داخل custom_erp)
# ============================================================================
# السبب: دور «Workspace Manager» يُظهر كل الموديولات للمستخدم ويحيد عن فلتر
# الإخفاء المركزي، فإسناده لأي مستخدم يُلغي التخفي عنه. هذه الطبقة تمنع
# الإسناد عبر حدث validate على User/Role Profile (آلية Hooks الرسمية، بلا
# أي تعديل على نواة Frappe).
#
# القائمة تُدار من config.py: MODULE_CONTROL["protected_roles"].
# ============================================================================

import frappe
from frappe import _
from frappe.utils import cstr

from custom_erp.custom_app.module_control.config import get_conf


def _protected_roles():
	"""Names of roles forbidden for assignment (normalized)."""
	return get_conf().get("protected_roles") or []


def _forbidden_rows(doc, child_field):
	"""Rows of `child_field` whose role is in the protected list."""
	roles = _protected_roles()
	if not roles:
		return []
	protected = {cstr(r).lower() for r in roles}
	rows = []
	for row in doc.get(child_field) or []:
		if cstr(getattr(row, "role", "")).strip().lower() in protected:
			rows.append(row)
	return rows


def enforce_protected_role_disabled(doc, method=None):
	"""Role.before_validate hook: keep protected roles DISABLED permanently.

	المطلب: «محجوبة ومعطلة — لا يستطيع تفعيلها لأي مستخدم».
	Setting `disabled=1` lets Frappe core's own Role.validate() call
	remove_roles() (removes the assignment from every user) automatically.
	Re-enabling from the Role form is impossible while this hook is wired.
	"""
	name = cstr(getattr(doc, "name", "") or "").strip().lower()
	protected = {cstr(r).strip().lower() for r in _protected_roles()}
	if name and name in protected:
		if not doc.disabled:
			doc.disabled = 1
			frappe.msgprint(
				_(
					"الدور «{0}» محميّ النظام: معطّل دائماً ولا يمكن إسناده لأي مستخدم "
					"(التعطيل يزيله تلقائياً من كل المستخدمين)."
				).format(doc.name),
				indicator="orange",
			)


def validate_user_role_assignment(doc, method=None):
	"""User.validate hook: forbid assigning protected roles.

	Raises a clear Arabic error; the save is refused until the row is removed.
	"""
	rows = _forbidden_rows(doc, "roles")
	if not rows:
		return
	frappe.throw(
		_(
			"الدور «{0}» ممنوع إسناده لأي مستخدم — لأنه يُظهر كل الموديولات ويلغي التخفي "
			"المركزي. أزل إسناد هذا الدور ثم احفظ مرة أخرى."
		).format("، «".join(cstr(row.role).strip() for row in rows)),
		frappe.PermissionError,
	)


def validate_role_profile_assignment(doc, method=None):
	"""Role Profile.validate hook: forbid adding protected roles to a profile."""
	rows = _forbidden_rows(doc, "roles")
	if not rows:
		return
	frappe.throw(
		_(
			"لا يمكن إضافة الدور «{0}» إلى ملف دور (Role Profile) — لأنه يُظهر كل "
			"الموديولات ويلغي التخفي المركزي."
		).format("، «".join(cstr(row.role).strip() for row in rows)),
		frappe.PermissionError,
	)


def remove_protected_role_assignments(source="Guard"):
	"""One-time / maintenance cleanup: strip protected roles from all users.

	Returns a list of dicts with the users cleaned. Also writes audit entries
	so the removal itself is traceable.
	"""
	from custom_erp.custom_app.module_control.audit import log as audit_log

	roles = _protected_roles()
	if not roles:
		return []
	rows = frappe.get_all(
		"Has Role",
		filters={"role": ["in", roles], "parenttype": "User"},
		fields=["name", "parent", "role"],
	)
	cleaned = []
	for row in rows:
		try:
			frappe.db.delete("Has Role", row.name)
			cleaned.append(row.parent)
			audit_log(source, "User", row.parent, cstr(row.role), "", "Info",
				"أزيلت صلاحية محميّة (Workspace Manager) لأنها تُظهر كل الموديولات")
		except Exception:
			frappe.logger("module_control").error(frappe.get_traceback()[:2000])
	if cleaned:
		frappe.db.commit()
	try:
		frappe.clear_cache()
	except Exception:
		pass
	return cleaned


def show_existing_assignments():
	"""Report-only: who currently holds protected roles (no writes)."""
	roles = _protected_roles()
	if not roles:
		return []
	rows = frappe.get_all(
		"Has Role",
		filters={"role": ["in", roles], "parenttype": "User"},
		fields=["parent", "role"],
		order_by="parent",
	)
	return rows
