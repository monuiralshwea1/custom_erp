# CONFIGURATION — إعدادات النظام وأولوياتها

## 1. مصدر الإجبار من Python — `module_control/config.py`

```python
MODULE_CONTROL = {
    "enabled": None,                   # None = يتبع إعداد DocType | False = إيقاف إجباري كلي
    "global_visibility": None,         # None | True | False
    "access_blocking": None,           # None | True | False (يفرض حظر الوصول مهما كانت الواجهة)

    "forced_hidden_modules": [],       # أمثلة: ["Projects", "Integrations", "Assets", "CRM"]
    "forced_hidden_workspaces": [],    # مثال: ["Build"]
    "forced_blocked_modules": [],      # حظر فعلي إجباري من Python

    # مساحات تظهر لمسؤول النظام (Administrator) فقط — تُنشأ تلقائياً عند أول
    # مزامنة إن لم تكن موجودة (PRIVATE: public=0 + for_user="Administrator").
    # القيمة = حقل Label. الإخفاء عن الجميع الآخرين مفروض بغض النظر عن الصلاحيات.
    "admin_only_workspaces": ["إدارة التطوير"],

    # أدوار معفاة من الإخفاء البصري كلياً (Q2-lite): مستخدم يملك أي دور من
    # القائمة يرى الموديولات/المساحات المخفية. لا يعفيه من حظر الوصول الفعلي
    # ولا من قواعد admin_only_workspaces.
    "visibility_exempt_roles": [],

    "apply_to_administrator": True,    # الإخفاء البصري يسري على Administrator
    "apply_to_workspace_manager": True,
    "apply_to_system_manager": True,

    "protected_api_scope": "app",      # "app" (حظر /api/method/{app}.* للقواعد المفعلة) | "none"
    "enforced_by": "Custom App",
}
```

**الحالة الحالية على الإنتاج: كل القوائم الإجبارية فارغة عمداً** — لسلوك افتراضي آمن. الاستثناء الجديد: `admin_only_workspaces = ["إدارة التطوير"]` (مساحة لوحة التخصيص، Administrator فقط). لا يوجد شيء مخفي إلا ما يجعله المسؤول من الواجهة أو مساحة إدارة التطوير أعلاه؛ حظر الوصول الافتراضي مُطفأ.

### مساحة «إدارة التطوير» (Admin-Only Workspace)

- تُنشأ تلقائياً في أول `run_sync()`/migrate إن لم تكن موجودة (`sync.ensure_admin_only_workspaces()` — idempotent آمن للتكرار).
- آلية إخفائها عن غير الأدمن **مستقلة تماماً** عن `enable_global_workspace_filter`، `strict_visibility_mode`، و`visibility_exempt_roles`: لا يراها أي مستخدم غير Administrator مهما كانت صلاحياته، وحتى إذا انقلبت أعلام التصفية كلها.
- لإضافة مساحة أخرى للحصر: أضف الـLabel إلى `admin_only_workspaces` ثم شغّل مزامنة — ستُنشأ بنفس النمط (اختصارات فارغة + بطاقة روابط أساس).

### مثال تفعيل فرض من Python (مُجرّب بنية ولكن القوائم فارغة لأنها لا تدخل الاختبار)

```python
"forced_hidden_modules": ["Projects", "CRM"],
```
ثم المزامنة:
```bash
# ملف: /tmp/dosync.py (كما في INSTALLATION)
cd /home/newsmart/frappe-bench2 && env/bin/python /tmp/dosync.py
```
النتيجة: قاعدة `Projects` تُضام تبقّى `enforced_by = "Custom App"`، ولا يمكن إلغاؤها من الواجهة (زر الإخفاء معطّل وظهور تنبيه).

## 2. إعدادات DocType — `Module Control Settings`

| الإعداد | الوصف | الافتراضي |
|---|---|---|
| enabled | تفعيل النظام كاملاً | 1 (كُتب تلقائياً في أول sync) |
| enable_global_workspace_filter | تصفية ظهور المساحات في البوت/Sidebar | 1 (حالة الموقع الحالية) |
| enable_access_blocking | طبقة الحظر الفعلية على الخادم | 0 |
| strict_visibility_mode | فرض الإخفاء حتى مع مستخدمين معفيين (config flags) | 0 |
| enable_audit_logging | تسجيل التغييرات في Audit Log | 1 |
| default_behavior_for_new_modules | `Follow Config` / `Visible To Everyone` / `Hidden By Default` | Follow Config |
| configuration_version | عدّاد الإصدار (auto) — مفتاح الكاش | يُرقّم تلقائياً |
| last_synchronization | آخر مزامنة | auto |

## 3. الجداول الفرعية

**Module Control Rule** (لكل موديول): `module`, `module_name`, `is_enabled`, `hide_module`, `block_module_access`, `hide_all_workspaces`, `hide_from_search`, `block_direct_navigation`, `block_protected_apis`, `enforced_by`, `description`.

**Workspace Control Rule** (لكل مساحة): `workspace`, `module`, `hide_workspace`, `block_direct_navigation`, `is_enabled`, `enforced_by`.

`enforced_by = "Custom App"` = قاعدة من Python (لا يمكن التعديل من الواجهة).

## 4. أولوية التنفيذ (من الأعلى للأدنى) — مُطبّقة في `visibility.build_state()`

0. **مساحات `admin_only_workspaces`**: تُطبق قبل كل شيء وباستقلال — تُخفى عن كل غير Administrator وتُحظر تنقلاً مباشراً، بلا استثناءات.
1. **قواعد الإخفاء/الحظر الإجبارية من Python** (`forced_*`) — تُعاد كتابتها قسراً في كل مزامنة.
2. **قواعد الحظر الإجبارية من Python** (`forced_blocked_modules`).
3. **إعدادات `Module Control Settings`** وقواعدها.
4. **سلوك Frappe الافتراضي**.

## 5. لغة الأولوية للنوافذ حسب المستخدم

| المستخدم | الإخفاء البصري | حظر الوصول |
|---|---|---|
| Administrator | يسري إذا `apply_to_administrator=1` (أو strict) — مُثبت فعلياً | **لا يسري** (bypass في نواة Frappe، مواثقه `frappe/permissions.py:94-96`) |
| Workspace Manager | يسري إذا `apply_to_workspace_manager=1` (أو strict) — مُثبت فعلياً | يسري |
| System Manager | يسري إذا `apply_to_system_manager=1` (أو strict) — مُثبت فعلياً | يسري |

## 6. الكاش والإصدار

- مفتاح الحالة: `custom_erp:module_control:state:d{version}` (redis) بـ TTL = 1800 ثانية.
- عدّاد الإصدار: `custom_erp:module_control:data_version` + مزامنة الحقل `configuration_version`.
- عند أي `Apply`/`restore_defaults`/migrate/بتغيّر `Module Def`/`Workspace`: bump + `frappe.clear_cache()` — مخدوم عبر multi-workers.

## 7. متغيّرات النظام التي تلمس الحظر الفعلي

- `EXCLUDED_DOCTYPES` (في `visibility.py`): مجموعة DocTypes النظام المحمية من الحظر الشامل (User, Role, DocType, Module Def, ... + رؤوس التحكم الخاصة بنا). لا تحذف منها إلا بمعرفة تبعاتها.
- DocTypes من موديول محظور تُفحَص وثيقةً بوثيقة عبر `Workspace` والأسماء.
