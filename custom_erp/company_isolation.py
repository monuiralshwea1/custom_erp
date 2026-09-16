import frappe


CUSTOM_COMPANY_FIELD = "custom_company"
COMPANY_LINK_DOCTYPE = "Company"

CUSTOM_COMPANY_DOCTYPES = {
	"Customer",
	"Item",
	"Supplier",
	"User",
}


def get_allowed_companies(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return []

	permissions = frappe.permissions.get_user_permissions(user).get(COMPANY_LINK_DOCTYPE, [])
	return [permission.get("doc") for permission in permissions if permission.get("doc")]


def is_company_restricted(user=None):
	return bool(get_allowed_companies(user))


def get_company_field(doctype):
	meta = frappe.get_meta(doctype)
	if meta.has_field("company"):
		return "company"
	if doctype in CUSTOM_COMPANY_DOCTYPES and meta.has_field(CUSTOM_COMPANY_FIELD):
		return CUSTOM_COMPANY_FIELD
	return None


def get_permission_query_conditions(user=None, doctype=None):
	if not doctype or user == "Administrator":
		return None

	company_field = get_company_field(doctype)
	if not company_field:
		return None

	allowed_companies = get_allowed_companies(user)
	if not allowed_companies:
		return None

	escaped_companies = ", ".join(frappe.db.escape(company) for company in allowed_companies)
	return f"`tab{doctype}`.`{company_field}` in ({escaped_companies})"


def has_permission(doc, ptype=None, user=None, **kwargs):
	user = user or frappe.session.user
	if user == "Administrator":
		return None

	company_field = get_company_field(doc.doctype)
	if not company_field:
		return None

	allowed_companies = get_allowed_companies(user)
	if not allowed_companies:
		return None

	company = doc.get(company_field)
	if not company:
		return ptype in ("create", "write")

	return company in allowed_companies


def apply_default_company(doc, method=None):
	if doc.doctype == "Company":
		return

	company_field = get_company_field(doc.doctype)
	if not company_field or doc.get(company_field):
		return

	allowed_companies = get_allowed_companies()
	if len(allowed_companies) == 1:
		doc.set(company_field, allowed_companies[0])


def validate_company_access(doc, method=None):
	if doc.doctype == "Company":
		return

	company_field = get_company_field(doc.doctype)
	if not company_field:
		return

	allowed_companies = get_allowed_companies()
	if not allowed_companies:
		return

	company = doc.get(company_field)
	if not company:
		frappe.throw(
			frappe._("Company is required for {0} when the user is restricted by company.").format(
				frappe._(doc.doctype)
			)
		)

	if company not in allowed_companies:
		frappe.throw(
			frappe._("You are not allowed to access company {0}.").format(frappe.bold(company)),
			frappe.PermissionError,
		)


def grant_company_to_creator(doc, method=None):
	user = frappe.session.user
	if not user or user == "Administrator":
		return

	_add_company_permission(user, doc.name, is_default=not is_company_restricted(user))
	_set_company_defaults(user, doc.name)


def sync_user_company_permission(doc, method=None):
	company = doc.get(CUSTOM_COMPANY_FIELD)
	if not company or doc.name in frappe.STANDARD_USERS:
		return

	_add_company_permission(doc.name, company, is_default=True)
	_set_company_defaults(doc.name, company)


def _add_company_permission(user, company, is_default=False):
	if frappe.db.exists(
		"User Permission",
		{"user": user, "allow": COMPANY_LINK_DOCTYPE, "for_value": company},
	):
		return

	permission = frappe.get_doc(
		{
			"doctype": "User Permission",
			"user": user,
			"allow": COMPANY_LINK_DOCTYPE,
			"for_value": company,
			"apply_to_all_doctypes": 1,
			"is_default": 1 if is_default else 0,
		}
	)
	permission.flags.ignore_permissions = True
	permission.insert()

	frappe.cache.hdel("user_permissions", user)


def _set_company_defaults(user, company):
	frappe.defaults.set_user_default("Company", company, user=user)
	frappe.defaults.set_user_default("company", company, user=user)
