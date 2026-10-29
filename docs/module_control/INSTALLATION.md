# INSTALLATION — التثبيت الكامل

هذه الأوامر تم تنفيذها فعلياً على الخادم (`192.168.0.248`, bench: `/home/newsmart/frappe-bench2`, site: `site1.local`) والنتائج موثقة كما ظهرت.

## 0. حالة ما قبل التثبيت (تم تنفيذها فعلياً)

```bash
# نسخة احتياطية قبل أي تعديل
mkdir -p /home/newsmart/backups_mc
cp /home/newsmart/frappe-bench2/apps/custom_erp/custom_erp/hooks.py \
   /home/newsmart/backups_mc/hooks.py.bak
```

## 1. نقل ملفات النظام داخل التطبيق (بنية النهائية)

```text
apps/custom_erp/custom_erp/custom_app/module_control/     # الحزمة الكاملة
  ├─ __init__.py
  ├─ config.py            # مصدر الإجبار من Python
  ├─ visibility.py        # حالة مركزية + كاش versioned
  ├─ workspace_filter.py  # غلاف desktop + boot_session
  ├─ permissions.py       # حظر الوصول (hooks + before_request)
  ├─ scanner.py           # جرد الموديولات + تحليل الاعتماديات
  ├─ sync.py              # محرك المزامنة/الفرض/التطبيق/الاسترجاع
  ├─ audit.py             # سجل التدقيق
  └─ api.py               # endpoints الواجهة (require_admin)
apps/custom_erp/custom_erp/custom_app/doctype/
  ├─ module_control_settings/    # Single
  ├─ module_control_rule/        # جدول فرعي
  ├─ workspace_control_rule/     # جدول فرعي
  └─ module_control_audit_log/
apps/custom_erp/custom_erp/public/js/module_control_settings.js
apps/custom_erp/custom_erp/public/css/module_control.css
apps/custom_erp/custom_erp/custom_app/tests/test_module_control.py
```

كما تُدمج الإضافات (`append`) إلى قسم الـHooks السفلي في `custom_erp/hooks.py` للمسارات التالية (بلا استبدال أي شيء موجود):

- `doc_events.update(...)` للـ `Module Def` و`Workspace`
- `after_install = [...]`، `after_migrate += [...]`
- `before_request = [...]`
- `boot_session = [...]`
- `has_permission.update({"*": ...})`، `permission_query_conditions.update({"*": ...})`
- `override_whitelisted_methods = {...}`
- `app_include_js += [...]`، `app_include_css += [...]`
- استدعاء `ensure_desktop_patched()` داخل try/except في نهاية الملف

## 2. تنفيذ migrate لتركيب الـ DocTypes (تم — ناجح)

```bash
cd /home/newsmart/frappe-bench2
bench --site site1.local migrate
```
النتيجة الفعلية: اكتملت المزامنة بنجاح، وظهرت DocTypes الأربعة في قاعدة البيانات، وأُنشئ `Module Control Settings` بتلقائية من النظام في أول مزامنة.

## 3. بناء الأصول (تم — ناجح)

```bash
bench build --app custom_erp
```
النتيجة: `DONE  Total Build Time: ...ms` ثم `Compiling translations for custom_erp`.

## 4. تأكيد مزامنة النظام (بديل `bench execute` — المشكلة محلولة والتسقيف في TROUBLESHOOTING)

سلوك `bench execute` في هذه البيئة يعاني من `eval` fallback (حدث `NameError: custom_erp is not defined`). البديل المُجرب:

```bash
# سكربت بايثون مباشر
/home/newsmart/frappe-bench2/env/bin/python /tmp/<script>.py
```

والمحتوى:
```python
import frappe
frappe.init(site="site1.local", sites_path="/home/newsmart/frappe-bench2/sites")
frappe.connect()
from custom_erp.custom_app.module_control import sync
print(sync.run_sync(source="Migration"))
frappe.destroy()
```
يجب تنفيذ السكربت من داخل مجلد الـ bench (`cd /home/newsmart/frappe-bench2`) — وإلا فشل logging (`FileNotFoundError: /home/logs/database.log`).
الناتج الفعلي: `{'enforced_flags': 0, 'disabled_invalid': 0, 'created_rules': [], 'initialized_defaults': True}` ثم `VERSION: 3` و`ENABLED: True`.

ملاحظة: لا حاجة لاستدعاء يدوي بعد أول `migrate` — الـ hook `after_migrate` يفعل المزامنة تلقائياً.

## 5. تحقق التثبيت (تم — ناجح)

```bash
# خلف HTTP: صفحة الواجهة والـ API
curl -s -b cookies http://192.168.0.248:8001/api/method/custom_erp.custom_app.module_control.api.get_overview | head
# أو (من داخل جلسة الدسكتوب)
# frappe.xcall('custom_erp.custom_app.module_control.api.get_overview', {})
```
النتيجة الفعلية: HTTP 200، `modules: 59`، إعدادات سليمة (`enabled:1, configuration_version:3`).

## 6. المطابقة بعد تحديث Frappe/ERPNext مستقبلاً

```bash
bench --site site1.local migrate      # يعيد التطبيق تلقائياً (after_migrate hook)
bench build
bench --site site1.local restart
```

## التثبيت من الصفر على موقع آخر

```bash
cd /home/<user>/frappe-bench
bench get-app <repo_url_custom_erp>
bench --site <site> install-app custom_erp
bench --site <site> migrate
bench build --app custom_erp
```
`after_install` hook سيتكفل بتهيئة `Module Control Settings` والقواعد المفروضة من config.py.
