import re

import frappe
from frappe.model.document import Document
from frappe.model.naming import get_default_naming_series, make_autoname


COMPANY_FIELD = "company"
CUSTOM_COMPANY_FIELD = "custom_company"


def apply_company_prefix(doc, method=None):
	if not doc.meta.autoname:
		return

	autoname = doc.meta.autoname.lower()
	company = doc.get(COMPANY_FIELD) or doc.get(CUSTOM_COMPANY_FIELD)
	if not company:
		return

	company_prefix = get_company_prefix(company)
	if not company_prefix:
		return

	if autoname.startswith("naming_series"):
		series = doc.naming_series or get_default_naming_series(doc.doctype)
		if series:
			doc.naming_series = prefix_series(series, company_prefix)
	elif autoname.startswith("field:"):
		fieldname = autoname[6:]
		if not doc.get(fieldname):
			series = doc.naming_series or get_default_naming_series(doc.doctype) or ".#####"
			prefixed_series = prefix_series(series, company_prefix)
			doc.set(fieldname, make_autoname(prefixed_series, doc=doc))


def get_company_prefix(company):
	abbr = frappe.db.get_value("Company", company, "abbr") or company
	abbr = frappe.safe_decode(abbr)
	prefix = re.sub(r"[^A-Za-z0-9]+", "-", abbr).strip("-").upper()
	if not prefix:
		return "COMP-"
	if not prefix.endswith("-"):
		prefix += "-"
	return prefix


def prefix_series(series, prefix):
	if series.startswith(prefix):
		return series

	# Preserve any leading dot or separator in the original series.
	if series.startswith("."):
		return prefix + series[1:]
	return prefix + series


class CompanySpecificNaming(Document):
	"""Backward compatibility for old cached documents.

	This class is kept so that Redis/doc caching can unpickle objects
	referring to custom_erp.company_sequence.CompanySpecificNaming.
	"""
	pass
