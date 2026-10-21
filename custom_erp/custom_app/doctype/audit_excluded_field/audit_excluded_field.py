# Copyright (c) 2026, moneer
# License: MIT

from frappe.model.document import Document


class AuditExcludedField(Document):
	"""استثناء حقل من تسجيل اسمه في سجل نشاط المستخدمين."""
