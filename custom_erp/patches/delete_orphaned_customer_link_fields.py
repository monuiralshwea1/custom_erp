# Copyright (c) 2026, moneer and contributors
# MIT License. See license.txt

"""Delete orphaned Customer link Custom Fields whose target DocTypes are missing.

Root cause: the app ``pos_next`` shipped ``Customer-custom_governorate``
(Link -> ``Governorate``) and ``Customer-custom_district`` (Link ->
``District``). On any site where ``pos_next`` (or another app providing those
DocTypes) is not installed, opening/adding a Customer throws::

    Field custom_governorate is referring to non-existing doctype Governorate.
    Please delete the field ... or add the required doctype.

(raised by ``frappe.desk.form.meta.FormMeta.add_search_fields`` on form load).

This patch deletes ONLY these two known fields and ONLY when their target
DocType is genuinely missing, so sites that do have ``Governorate`` /
``District`` keep their fields untouched. Safe to run on every server through
the normal ``bench migrate`` flow.
"""

import frappe

# (Custom Field name, expected target DocType)
ORPHAN_CANDIDATES = (
    ("Customer-custom_governorate", "Governorate"),
    ("Customer-custom_district", "District"),
)


def execute():
	for field_name, target_doctype in ORPHAN_CANDIDATES:
		if not frappe.db.exists("Custom Field", field_name):
			print(f"[orphan-fields] {field_name} not present, skipping")
			continue
		if frappe.db.exists("DocType", target_doctype):
			print(f"[orphan-fields] {target_doctype} exists, keeping {field_name}")
			continue
		frappe.delete_doc("Custom Field", field_name, force=True)
		print(f"[orphan-fields] deleted {field_name} (missing DocType {target_doctype})")
	frappe.db.commit()
