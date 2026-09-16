import frappe


CUSTOM_FIELDS = {
	"Customer": {
		"insert_after": "customer_group",
		"label": "Company",
	},
	"Supplier": {
		"insert_after": "supplier_group",
		"label": "Company",
	},
	"Item": {
		"insert_after": "item_group",
		"label": "Company",
	},
	"User": {
		"insert_after": "user_type",
		"label": "Company",
	},
}


def execute():
	for doctype, options in CUSTOM_FIELDS.items():
		_create_company_field(doctype, options)

	frappe.db.set_single_value("System Settings", "apply_strict_user_permissions", 0)


def _create_company_field(doctype, options):
	fieldname = "custom_company"
	name = f"{doctype}-{fieldname}"

	if frappe.db.exists("Custom Field", name):
		return

	custom_field = frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": doctype,
			"fieldname": fieldname,
			"fieldtype": "Link",
			"label": options["label"],
			"options": "Company",
			"insert_after": options["insert_after"],
			"translatable": 0,
		}
	)
	custom_field.flags.ignore_permissions = True
	custom_field.insert()
