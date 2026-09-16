import frappe


def execute():
	frappe.db.set_single_value("System Settings", "apply_strict_user_permissions", 0)
	_set_defaults_for_company_restricted_users()


def _set_defaults_for_company_restricted_users():
	permissions = frappe.get_all(
		"User Permission",
		filters={
			"allow": "Company",
			"is_default": 1,
		},
		fields=["user", "for_value"],
	)

	for permission in permissions:
		frappe.defaults.set_user_default("Company", permission.for_value, user=permission.user)
		frappe.defaults.set_user_default("company", permission.for_value, user=permission.user)
