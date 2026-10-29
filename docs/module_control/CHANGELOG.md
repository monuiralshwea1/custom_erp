# CHANGELOG — السجل الفعلي للتغييرات (site1.local، 2026-10-28)

جميع البنود أدناه نُفذت فعلياً على الخادم `192.168.0.248` داخل تطبيق `custom_erp`.

## [1.2.0] — 2026-10-28 — حجب واجهات المطور لغير Administrator + قفل دور Workspace Manager

### Added — حاجز واجهات «إدارة التطوير» (مستقل عن الإعدادات)

- **طبقة `DEV_DOCTYPES` + `DEV_ACCESS_MESSAGE`** في `module_control/permissions.py`:
  - دوختيبات: `Module Control Settings`، `Module Control Rule`، `Workspace Control Rule`، `Module Control Audit Log`.
  - الرسالة المطلوبة (من المستخدم): «ليس لك إذن الوصول لهذه الصفحة — خاصة بالمطوّر (أدوارها متاحة لحساب Administrator فقط)».
  - ثلاث نقاط حجب مستقلة — لا تقتصدي أي من مفتاحي `enabled`/`enable_access_blocking`:
    1. `has_permission_hook`: رفع `PermissionError` لأي ptype من عمليات STYPE (read/write/…) لغير Administrator.
    2. `query_conditions_hook`: رفع PermissionError لقوائم `get_list`/ListView.
    3. `before_request_hook`: حجب `/api/resource/{dev-doctype}` HTTP 403 قبل أن يصل الطلب للدوختيب.
  - نمط النواة المطابق (`desk/form/load.py` `flags.error_message`): `_dev_deny()` يضع `frappe.flags.error_message` قبل الرفع استجابةً `_error_message` في JSON ليضل يظهر الرسالة نفسها في بطاقة المنظم (msgprint) للـ SPA بدل الرسالة العامة.
- **`require_admin()` في `api.py` أصبح Administrator-ONLY** (أزيل السماح لدور System Manager — الذ يكان يسمح لـ moneer بفتح الأداة). تنطبق على كل نقاط النهاية `get_overview`/`apply_changes`/`import_config`/… .
- **`app_include_js` → `public/js/dev_gate.js`**: تجويد الرسالة على واجهة الديسكت فقط — يُعيد الحْمِل `frappe.show_not_permitted` ليطيير البطاقة الكاملة برسالة المطور (فقط عندما تكون الصفحة من واجهات التطوير)؛ الخادم هو الحاجز الحقيقي والـ JS مجرد عرض.
  - المثبت الحقيقي SPA: أول مطل من الواجهة النموذج هو `frappe.desk.form.load.getdoc` (وليس `frappe.client.get`) — ومن المحجوب 403 برسالتنا.

### Added — قفل دور Workspace Manager (محجوب ومعطل)

- **`role_guard.py`** + hook جديد `Role.before_validate` → `enforce_protected_role_disabled`:
  - أي محاولة إعادة التفعيل من نموذج الدور تُعاد فوراً إلى `disabled=1` مع msgprint «الدور محميّ النظام: معطّل دائماً…».
- **حاجزا الإسناد المؤكدين** على User وRole Profile (المصادر: doc_events).
- **حماية مزدوجة من نواة v15**: `Role.validate()` عند `disabled=1` ينادي `disable_role()` (يُزيل الإسناد من جميع المستخدمين)، و`User.validate()` سطر 189 `remove_disabled_roles()` يفرّغ أي صف `Has Role` لِدور معطّل عند الحفظ — أي إسناد يُحذف تلقائياً إذا حاول أي مستخدم تجاوز الحاجز.
- **مفتاح `protected_roles = ["Workspace Manager"]`** في `config.py` (`get_conf` يطبعها normalized) — لمنع أي دور إضافي مستقبلاً يكفي إضافتها للقائمة.

### Verified — بالتحقق الحي (متصفح + خادم)

- مستخدم حي (System Manager) من الواجهة SPA: الفتح `/app/module-control-settings` يُظهر بطاقة «غير مسموح به — ليس لك إذن الوصول لهذه الصفحة — خاصة بالمطوّر…» ولا يُجمّد النموذج. سجل التدقيق (`/app/module-control-audit-log`) يُحجب بنفس الرسالة. أما مسارات القوائم غير المسجلة (rules) فتُرفض بصفحة «المسار غير موجود».
- `moneer`/`smartqa`: `frappe.client.get/get_list` + `api.get_overview`/`export_config` — 403 بالرسالة. Administrator غير متأثر (نموذج الإعدادات يفتح طبيعياً + `get_overview` يعمل).
- عمليات الأعمال العادية سليمة (Company/Customer/Sales Invoice lists).
- Workspace Manager: `disabled=1`، صفر إسناد، محاولة إعادة التفعيل تُعطّله؛ الإسناد محجوب.
- حزمة الاختبارات بعد كل تعديل: `Ran 10 tests — OK (skipped=1)`.

> حاجز المطور لا يعتمد على أي إعداد — حتى لو توقف التطبيق كله لا يزيله. (تجاوز النواة الوحيد المتبقّ موثّقاً: أذونات مستوى المكتبة تُختصر عند Administrator في `frappe/permissions.py:94-96` — لا يهم لأن واجهة الديسكت تمرّ حصراً عبر HTTP/API.)

## [1.0.0] — 2026-10-28 — الإطلاق الأول (Central Module Control Manager)

### Added — البنية

- **حزمة `custom_erp/custom_app/module_control/`** (9 ملفات): config، visibility، workspace_filter، permissions، scanner، sync، audit، api، `__init__`.
- **DocTypes**: `Module Control Settings` (Single)، `Module Control Rule`، `Workspace Control Rule`، `Module Control Audit Log` (autoname hash) — تركّب تحت موديول `custom app` وتتليل من System Manager.
- **واجهة إدارة** `/app/module-control-settings`: جدول 59 موديول ببحت/فلاتر/جمعي/Preview/سجل، بنية RTL، Vue مُعالجة داخل النموذج `Module Control Settings`.
- **سجل تدقيق** يوثق كل حدث (7 عمليات حقيقية مسجلة في جولة الاختبار).
- **موأ SCM**: ملف `module_control.css`.

### Added — طبقات التنفيذ

1. **الإخفاء البصري المركزي** (تطبق للجميع، incl. Administrator/WM/SM):
   - `boot_session` filter + غلاف `frappe.desk.desktop.get_workspace_sidebar_items` + `get_desktop_page` (module-attr patch documented, idempotent)
   - `override_whitelisted_methods` للتحليل HTTP الرسمي (عن صلاحٍ `@frappe.whitelist()`)
   - حظر التنقل المباشر للمساحة المخفية: message عربي «مساحة العمل {0} غير متاحة»
2. **حظر الوصول الفعلي** (اختياري لكل قاعدة):
   - MD-level (`has_permission["*"]`, `permission_query_conditions["*"]`)
   - مسارات API (before_request): `/api/resource/{doctype}` + `/api/method/{app}.*` ( Sciences اختيريةاً) — خروج 403 عربي.
3. **قواعد فرض Python** (config.py) مع منع التجاوز من الواجهة.
4. **sync engine**: أ认为是 first-run، `run_sync` idempotent، bump version + clear_cache، تسارع doc_events (Module Def/Workspace عبر enqueue + lock 60s)، migrate/install hooks.
5. **Audit log**: doc-type منفصل + `audit.py`.

### Fixed — أثناء التحقيق الحي

- `module_icon` غير موجود في بنية Module Def (بالموقع) — إزالته من scanner.
- `frappe.get_all(pluck=)` ترجع strings، تُظبط تساعدة `set()`.
- `bench execute` تعطل بسبب eval fallback — موثق، والبديل الذي نُفذ: سكربت بايثون مباشر (INSTALLATION).
- Lacking المؤشر الأول: `first-run defaults` (enabled=1، audit=1) عبر `initialized_defaults`.
- `override targets` تتطلب `@frappe.whitelist()` — إضافة عاكس.
- إزالة `cmd`/`lang` من الحجج قبل التفويض في دوال الاستبدال.
- يعمل handled شخص `page` نوعين (str JSON/ dict) في `wrap_get_desktop_page` — السبب: router الحقيقي يمرّر JSON string.
- `frappe.utils.unescape_html` غير موجود → تُستخدم `urllib.parse.unquote`.
- `apply_changes` مع `audit=False` → `UnboundLocalError` (مُكتشف من حزمة الاختبارات) — مُصلح.
- `protected_apps` الحساب المشهد على العلم `block_protected_apis` لا على مجرد block (تعويض الحظر الإجمالي غير المقصود للموقع الكامل).

### Verified — الجولة الحيّة على Projects (كلها ناجحة)

- boot/sidebar/admin/WM filtered (67/52/67 بدون Projects)
- التنقل المباشر محجوب؛ مساحة مرئية (Accounting) سليمة؛ العودة بعد الإكتشاف و100% rollback
- Access blocking: 403 على `/api/resource/Project` (قائمة/مستند/إنشاء)، `frappe.client.get`، `frappe.client.insert`، تقرير `Project Summary`، تقرير تا في User `get_list` (invisible)
- Administrator: visual-hidden نافذة (67)؛ core bypass على حظر الوصول (True has_permission) — documented
- block_protected_apis: erpnext.* 403، frappe.* 200؛ صعيد الإزالة استعادة الـ 200
- Audit: 7 سجلات سليمة بالمستخدم/الوقت/قبل-بعد
- Auto tests: `Ran 8 tests ... OK (skipped=1)`

### Documentation

- `docs/module_control/` (11 ملفاً — بما فيها هذا السجل) بأوامر ونتائج منفذة فقط.

## [1.1.0] — 2026-10-28 — مساحة «إدارة التطوير» + الاستيراد + فحص التوافق + الترجمة

### Added

- **مساحة عمل «إدارة التطوير» (Admin-Only)**:
  - مفتاح `admin_only_workspaces = ["إدارة التطوير"]` في `config.py` + `sync.ensure_admin_only_workspaces()` تُنشئها تلقائياً عند أول مزامنة (PRIVATE: `public=0`، `for_user="Administrator"`، module `custom app`).
  - المحتوى: 6 اختصارات (لوحة التحكم ⚙️، سجل التدقيق 🧾، الموديولات 🧩، المساحات 🗂️، قواعد المساحات 🧱، أنماط الصفحات 📄) + بطاقة روابط «التحكم في الموديولات» (Module Control Settings / Audit Log / Module Def / Workspace / Workspace Control Rule).
  - فرض مزدوج مستقل عن أي صلاحيات: الإخفاء لكل مستخدم غير Administrator في boot/sidebar (`_filter_admin_only` — يعمل حتى مع الإعفاءات) و`module_wise_workspaces`، وحظر التنقل المباشر عبر `get_desktop_page` برسالة عربية 403: «مساحة العمل {0} متاحة لمسؤول النظام (Administrator) فقط».
  - **مُثبت حياً** (بما فيه فحص المتصفح الفعلي بتسجيل دخول حقيقي): Administrator يرى 69 صفحة (فيها «إدارة التطوير» أولاً)؛ المستخدمون الآخرون بلاها (smartqa 53، moneer 37)؛ التنقل المباشر محجوب 403؛ ولا تسريب في `module_wise_workspaces`؛ المساحة تُفتح وتعرض 6 اختصارات + بطاقة روابط بالـDocTypes الخمسة.
- **تسمية متوافقة مع راوتر Frappe للمساحات الخاصة**: مساحات Frappe الخاصة تُسمى `<title>-<user>` (سلوك نواة `workspace.js`) ليعمل الراوتر؛ `ensure_admin_only_workspaces` يسمّي بالمثل (name/label سابقة اللاحقة، `title` نظيفاً)، ويعمل ترحيل تلقائي للحالة القديمة (rename) مع الحفاظ على الاختصارات والروابط.
- **ما يظهر للمستخدم المسؤول**: عنوان المساحة نظيف «إدارة التطوير»، الترويسة «🛠️ إدارة التطوير — مركز التحكم في الموديولات والتخصيصات (للمسؤول فقط)»، 6 اختصارات، بطاقة «التحكم في الموديولات» بروابط عربية مترجمة (routes صحيحة).
- **حوار الاستيراد مكتفي بأزراره الداخلية**: على هذا الموقع تعمل سكربتات تعديل أزرار عالمية (navigation_buttons_force/global_button) تعترض `.btn-primary`; لذا المعاينة/التأكيد/الإلغاء أزرار مستقلة داخل جسم الحوار لضمان العمل دوماً.
- **الترويسة والبطاقة بالترجمة العربية** — زر فحص التوافق: **13/13 نقطة ✅**؛ معاينة الاستيراد تعرض «لا يوجد فرق» للتصدير المطابق.
- **Q4 — استيراد الإعدادات**: `api.import_config(config, preview)` يقبل `{"settings": snapshot}` أو snapshot مجردة؛ `preview=1` يعيد الفرق دون أي كتابة؛ الاستيراد الفعلي يمر عبر `sync.apply_changes(source="Import")` (bump + clear_cache + audit). زر واجهة «⬇ استيراد الإعدادات» (معاينة → تأكيد → تطبيق).
- **Q8 — فحص التوافق**: `api.compat_check()` يفحص كل نقاط التكامل مع نواة Frappe (سمات desktop، علم الـpatch، `urllib.parse.unquote`، `frappe.boot.load_desktop_data`، وجود الـhooks، أهداف override، مفاتيح build_state والمفاتيح الستة في config.py). زر واجهة «🧪 فحص التوافق» يعرض جدولاً ✅/❌.
- **Q2-lite (أدوار معفاة)**: مفتاح `visibility_exempt_roles: []` في `config.py`؛ أي مستخدم يملك دوراً من القائمة يُعفى من الإخفاء البصري (بعد فحص admin/WM/SM؛ لا يعفى من قواعد admin-only ولا من حظر الوصول الفعلي).
- **الترجمات**: +58 سطراً في `custom_erp/translations/ar.csv` (236 → 294 سطراً) تغطي أسماء DocTypes، تسميات الحقول، رسائل النظام («Enforced by Custom App»، Import/Export Config، Compatibility Check، «إدارة التطوير»...).

### Verified

- إنشاء/ترحيل المساحة: تسمية الراوتر الصحيحة `إدارة التطوير-Administrator` (العرض «إدارة التطوير»)؛ المستند: `(name='إدارة التطوير-Administrator', title='إدارة التطوير', public=False, for_user='Administrator', module='custom app')`.
- **فحص المتصفح الفعلي (دخول حقيقي Administrator)**: Sidebar 69 عنصراً «إدارة التطوير» أولاً؛ المساحة تفتح عبر `/app/private/إدارة-التطوير` وتعرض الترويسة + الاختصارات الستة + بطاقة «التحكم في الموديولات» بـ5 روابط مترجمة؛ زر فحص التوافق: **13/13 ✅**؛ حوار الاستيراد: المعاينة تظهر وتُلغى بلا كتابة.
- حزمة الاختبارات: `Ran 10 tests in 14.280s — OK (skipped=1)` (اختباران جديدان: `test_admin_only_workspace_visibility` — محدثاً لتسمية الراوتر، `test_import_config_preview_no_write`).
- `bench build --app custom_erp` نجح عدة مرات (آخر: 4.3s) بظهور الزرّين والحوار الداخلي.


