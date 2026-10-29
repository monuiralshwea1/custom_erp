# DEVELOPER_GUIDE — البنية الداخلية وHooks وAPI

## 1. خريطة الملفات

```text
custom_erp/custom_app/module_control/
├─ __init__.py
├─ config.py          # MODULE_CONTROL + get_conf(): التطبيع والإجبار من Python
├─ visibility.py      # EXCLUDED_DOCTYPES، get_version/bump_version، build_state/get_state، user_is_exempt
├─ workspace_filter.py # الغلاف الموثق على frappe.desk.desktop + boot_session + override targets
├─ permissions.py     # has_permission_hook، query_conditions_hook، before_request_hook
├─ scanner.py         # get_module_inventory، refresh_inventory، get_dependency_impact (cache 1h)
├─ sync.py            # run_sync، after_settings_saved، apply_changes، compute_diff، restore_defaults
├─ audit.py           # log() into Module Control Audit Log (idempotent, fail-safe)
└─ api.py             # @frappe.whitelist: get_overview، sync_now، scan_modules، ...
```

DocTypes: `module_control_settings/` (Single), `module_control_rule/`, `workspace_control_rule/`, `module_control_audit_log/` — علومهم `custom app`.

## 2. فهم تفرع التأثير للتخزين والاستدعاء (نُثبت في المصدر المثبت v15)

نقاط الالتقاء الموثقة في الـ hooks:

1. **`boot_session`** (frappe/boot.py الخط 95) — ينبع بعد `load_desktop_data`، فنقوم بتصفية `bootinfo.allowed_workspaces` و`module_wise_workspaces`.
2. **`override_whitelisted_methods`**:
   - `frappe.desk.desktop.get_workspace_sidebar_items` → `*.workspace_filter.get_workspace_sidebar_items_filtered`
   - `frappe.desk.desktop.get_desktop_page` → `*.workspace_filter.get_desktop_page_filtered`
   **شرط مهم مُتحقق**: يجب أن تكون دوال الاستبدال `@frappe.whitelist()`، وإلا فشل كل استدعاء HTTP للتوابع الأصلية (403 not whitelisted) — مُجرّب وأُصلح.
   **ملاحظة استدعاء**: `frappe.call` يحقن `cmd`/`lang` في الحجج — لا بد إزالتها قبل التفويض.
3. **مظلة الإجبار الداخلي (direct-import callers)**: `frappe/boot.load_desktop_data` و`frappe/apps.get_apps` يستوردان التابع مباشرة، فيتجاوزان الاستبدال. الحل الموثق: **غلاف module-attribute** (`ensure_desktop_patched`) بشئَ موحد مع مكثف في نفس النمط (`tajer_erp.customizations.workspace_access_customization`).
   - idempotent (فحص `_custom_erp_mc_desktop_patched`).
   - لا يمنح أي صلاحيات؛ فقط يزيل العناصر المخفية للجميع.
   - يفهم `page` كسلسلة JSON (ما تمرّهُ الـ router الحقيقي) أو ككائن.

4. **حظر الوصول على مستوى المستند**
   - `has_permission["*"]` → `has_permission_hook(doc, ptype, user)` عبر `has_controller_permissions` (frappe/permissions.py 450+): ثم `return False` للرفض.
   - `permission_query_conditions["*"]` → `query_conditions_hook(user, doctype)` ترجع `"1=0"` لchess الاسم `"tabWorkspace"` المُستبقي غلفة سلوكية عبر `EXCLUDED_DOCTYPES` + flags:
       - **Administrator مستثنى هنا**: تعالب الفحص الأصلي في `frappe.permissions.has_permission` — لا يصل إلى الرفض لأن admin يمرس قبلها في النواة (إن كان ليس معنا عن المستويات).
5. **حظر المسار API — `before_request`** (frappe/app.py 200-203):
   - `/api/resource/{doctype}` (بفك ترميز العنوان عبر `urllib.parse.unquote`) → 403 برسالة PermissionError عربية.
   - `/api/method/{app}.*` — يُحجم فقط إذا كانت قاعدة الموديول تعلم `block_protected_apis=1` (متكافأ مع Python-Forced) و`protected_api_scope == "app"`؛ `custom_erp.*` مستثنى.
   - التفصيل: عند `audit=False` أصل من bugs المكتشفة `UnboundLocalError` في `apply_changes` — تم صياغته، وشُرح في TESTING — والسبب: فرق changes لمكان التعُمّم.

6. **`doc_events`**: بعد `Module Def.on_update/after_insert` و`Workspace.*` → `_autosync_queue` (قفل 60s + queue=short) — لا يسبب save-في حلقة (Labels من Recommended flags).

## 3. الحالة المركزية والقراءة النموذجية

```python
from custom_erp.custom_app.module_control.visibility import get_state, get_version, bump_version, user_is_exempt
state = get_state()   # dict: enabled/global_filter/access_blocking/strict/hidden_modules/...
群岛 READ: state["hidden_workspaces"], state["hidden_modules"], state["blocked_doctypes"]
```

**قواعد الأمان عند قراءة الحالة:** in function-helpers المستخدمة دولياً:
```python
if not state["enabled"]: ...   # لا فرض
```

## 4. الحفظ/الفرض في `sync.py`

- `run_sync(source)`: أثناء أول تفعيل يعبّئ الافتراضات تبعاً للإعدادات، ثم:
  - إنشاء القواعد وفرضها على `forced_hidden_modules/forced_blocked_modules/forced_hidden_workspaces`.
  - رفع فرض القواعد التي أزيلت من config.py (enforced_by فارغة).
  - **المثال الفعلي الأول**: `initialized_defaults: True` + `VERSION 3`.
- `apply_changes(payload, source, bump, audit)` — الحفظ ثم الفرض ثم `bump_version` + `frappe.clear_cache` + audit diff.
- `compute_diff(old, new)` — عرض الفرق الحقيقي بالعربية.
- `restore_defaults()` — إزالة كل ما يملكه النظام (بأمان).
- `after_settings_saved` — ربط من DocType `on_update` (مع حماية من التrecursive).
- `setup_after_install`, `after_migrate`, `on_module_changed`, `on_workspace_changed` (نقاط الربط في hooks).

## 5. واجهة إدارة API (كلها `require_admin()`)

| endpoint | التحليل | البرهان الفعلي |
|---|---|---|
| `get_overview` | Dispatcher Grid الكامل (59) + إعدادات القواعد + audit آخر 25 | 200, verified |
| `scan_modules` | جرد Mih | 200, count 59 |
| `get_module_impact` | اعتماديات doc-level links + reports | يُبرهن في الـ UI |
| `preview_changes` | فرق نظري + تحذيرات مخاطر | "0→1" verified |
| `save_and_apply` | الحفظ + bump + clear_cache + audit | 200 verified |
| `restore_defaults` | إزالة يملكه النظام فقط | Verified |
| `get_audit_log` | آخر N عمليات | Verified (7 rows) |
| `export_config` | تصدير snapshot (JSON) | Implemented |

### إضافة وظيفة مستقبلية؟

```python
# 1) خيار المستند: أضف الحقل في module_control_settings.json + قواعد-الطعن
# 2) تقدم القواعد: visibility.build_state/modul" + sync.apply/restore
# 3) doc_events: direct configuration
```

## 6. الهيكل الداخلي الذي لا يجب تغييره في Frappe Core

الاستثمار in Frappe v15 المثبت: `frappe/app.py:200-203` (before_request)، `frappe/boot.py:95/181` (boot_session/allowed_workspaces)، `frappe/permissions.py:76-100` (Administrator bypass + has_permission hooks)، `frappe/apps.py:18-20`، `frappe/model/db_query.py:1116-1131` (query-conditions).

- **لا تعدّل Frappe Core أبداً** — البديل: الجاسوري الموصوف أعلاه (module-attr wrapper idempotent) الذي يظل معزولًا داخل `custom_erp` ومرقى الشفط.
