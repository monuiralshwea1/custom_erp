# -*- coding: utf-8 -*-
"""
Central Module Control Manager — Python-level configuration.

هذا الملف هو مصدر الإجبار (Source of Authority) لإعدادات النظام المركزي.
أولوية التنفيذ (من الأعلى إلى الأدنى):
  1. قواعد الإخفاء الإلزامية هنا (forced_hidden_*)
  2. قواعد الحظر الإلزامية هنا (forced_blocked_modules)
  3. إعدادات DocType: Module Control Settings
  4. السلوك الافتراضي في Frappe

أي وحدة واردة هنا:

- لا يمكن إظهارها من واجهة الإدارة (تُعاد قيمها تلقائياً عند كل مزامنة).
- تبقى مخفية بعد التحديث أو migrate أو إعادة تشغيل الخادم.

استخدم الأسماء الداخلية (Internal names) وليس العناوين المترجمة، مثال:
    MODULE_DEF راجع قائمة Module Def الحقيقية في قاعدة البيانات.
"""

MODULE_CONTROL = {
	# إيقاف/تشغيل النظام كاملاً. None = يتبع إعداد DocType، False = إيقاف إجباري كلي.
	"enabled": None,

	# التصفية العامة لظهور المساحات (Workspaces) في واجهة التنقل.
	# None = يتبع إعداد DocType.
	"global_visibility": None,

	# طبقة حظر الوصول الفعلي على الخادم. None = يتبع إعداد DocType.
	"access_blocking": None,

	# موديولات مخفية إجبارياً من واجهة الاستخدام (تظهر كـ "Enforced by Custom App").
	# أمثلة: ["Projects", "Integrations", "Assets", "CRM"]
	"forced_hidden_modules": [],

	# مساحات عمل مخفية إجبارياً بالاسم الداخلي الواحد.
	# مثال: ["Build"]
	"forced_hidden_workspaces": [],

	# موديولات محظور الوصول إليها إجبارياً (طبقة الأمان على الخادم، لا تُستخدم للإخفاء البصري).
	"forced_blocked_modules": [],

	# مساحات عمل تظهر لمسؤول النظام (Administrator) فقط.
	# تُخفى إجبارياً عن كل المستخدمين الآخرين بغض النظر عن صلاحياتهم أو أي إعدادات أخرى،
	# ويُحظر الوصول المباشر إليها. تُنشأ تلقائياً عند أول مزامنة إن لم تكن موجودة.
	# القيمة = حقل Label (اسم المساحة).
	"admin_only_workspaces": ["إدارة التطوير"],

	# أدوار معفاة من الإخفاء البصري كلياً (مستقبل per-role):
	# أي مستخدم يملك دوراً من هذه القائمة يرى كل الموديولات المخفية من الواجهة.
	"visibility_exempt_roles": [],

	# أدوار ممنوع إسنادها لأي مستخدم (يُحفظ على المستخدم فوراً برسالة عربية).
	# سبب الدور الافتراضي «Workspace Manager»: يُظهر كل الموديولات للمستخدم
	# ويحيد عن فلتر الإخفاء المركزي، فإسناده لأي مستخدم يُلغي التخفي عنه.
	"protected_roles": ["Workspace Manager"],

	# هل يشمل الإخفاء البصري مستخدم Administrator؟ (تشمل بالسلوك الافتراضي True)
	"apply_to_administrator": True,

	# هل يشمل الإخفاء البصري دور Workspace Manager؟
	"apply_to_workspace_manager": True,

	# هل يشمل الإخفاء البصري دور System Manager؟
	"apply_to_system_manager": True,

	# نطاق حظر المحمي APIs خاصية block_protected_apis:
	#   "app"  = حظر /api/method/{app_name}.* لأي تطبيق ذات صلة بالموديول المحظور
	#   "none" = لا حظر على مستوى مسارات method (اعتمد حظر /api/resource فقط)
	"protected_api_scope": "app",

	# تسمية القواعد المفروضة من هذا الملف ضمن الواجهة.
	"enforced_by": "Custom App",
}


def get_conf():
	"""Return validated copy with normalized values (booleans or None)."""
	c = dict(MODULE_CONTROL or {})

	def _norm(v):
		if v is None:
			return None
		return bool(v)

	out = {}
	for k in ("enabled", "global_visibility", "access_blocking"):
		out[k] = _norm(c.get(k))
	for k in ("apply_to_administrator", "apply_to_workspace_manager", "apply_to_system_manager"):
		out[k] = True if c.get(k) is None else bool(c.get(k))
	for k in ("forced_hidden_modules", "forced_hidden_workspaces", "forced_blocked_modules", "admin_only_workspaces", "visibility_exempt_roles", "protected_roles"):
		raw = c.get(k) or []
		out[k] = [str(x).strip() for x in raw if x and str(x).strip()]
	out["protected_api_scope"] = "app" if c.get("protected_api_scope", "app") == "app" else "none"
	out["enforced_by"] = c.get("enforced_by") or "Custom App"
	return out
