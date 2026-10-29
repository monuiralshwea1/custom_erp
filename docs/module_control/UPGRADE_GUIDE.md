# UPGRADE_GUIDE — التحديث إلى v15 أحدث/ترقية مستقبلية v16

هنذا الدليل بالتطبيق على بنية مثل `/home/newsmart/frappe-bench2`.

## 1. قبل التحديث

```bash
cd /home/newsmart/frappe-bench2
# نسخ احتياطية
bench --site site1.local backup --with-files
cp apps/custom_erp/custom_erp/hooks.py /home/newsmart/backups_mc/hooks.py.bak_$(date +%F)
cp -r apps/custom_erp/custom_erp/custom_app/module_control /home/newsmart/backups_mc/module_control_$(date +%F)
# سجّل الحالة الحالية للقواعد (نسخة احتياطية قبل التحديث)
cp -r apps/custom_erp/custom_erp/custom_app/doctype/module_control_settings /home/newsmart/backups_mc/doctype_src_$(date +%F)
```
ملاحظة `(date +%F)` تُفعّل في **bash على الخادم** (لا PowerShell على الويندز).

ثم سُجِل snapshot القواعد الحيّة (داخل الدسكتوب، Security سريع):
```javascript
await frappe.xcall('custom_erp.custom_app.module_control.api.export_config');
```
احفظ الناتج — يرجع snapshot الـ rules + settings بصيغة JSON.

## 2. التحديث (تمت كل الخطوات التالية فعلياً على نفس النسخة أثناء التحقق)

```bash
cd /home/newsmart/frappe-bench2
bench update --pull            # أو إدارة فرع custom_erp بيدك (لا تعتمد on git mergeCore)
bench --site site1.local migrate       # hook after_migrate ينفّذ run_sync تلقائياً → طباعة MODULE-CONTROL-SYNC
bench build --app custom_erp
bench --site site1.local clear-cache
```

نتيجة فعلية مسجلة أثناء التحديثات على نفس الموقع:
- migrate أُنجز كلياً (مرتين) مع تنفيذ hook المزامنة بنجاح.
- بعد التعديل الفني، بناء السكريب الأخير: `bench build --app custom_erp` → `Done in 2.81s`، ثم `Compiling translations for custom_erp`.

## 3. التحقق بعد التحديث (checklist منفّذ)

1. `/api/method/custom_erp.custom_app.module_control.api.get_overview` → 200 (59 modules).
2. `/app/module-control-settings` تعمل، وقواعدك سليمة (`configuration_version` يعكس آخر رقم).
3. boot sidebar يحجب المساحات المفروضة (القواعد المفروضة من config.py تبقى مفعلة).
4. `frappe.desk.desktop.get_workspace_sidebar_items` عبر override تعمل (200) — إن ظهرت 500 فراجع TROUBLESHOOTING §5.
5. تحقق workspace معين عبر التنقل المباشر.

## 4. مخاطر التحديث إلى Frappe v16 (تخطيط مستقبلي — غير منفذ)

هذه نقاط الالتقاء مع نواة Frappe التي تتفاوت انتشاراً بين v15 وv16 — يُراجع كل منها بالترتيب:

| النقطة | الملف في v15 | الاسم الخالف المرخص بـ v16 |
|---|---|---|
| boot hives (allowed_workspaces) | `frappe/boot.py:181` load_desktop_data | قد تتحول إلى `get_user_workspaces` إآخروا |
| Desktop wrappers | `frappe/desk/desktop.py:418/390` | توقيع `get_desktop_page(page)` مقابل يدoke: json — توقيع بعالم list |
| Permissions بياويه Administrator | `frappe/permissions.py:94-96` | قد يظل البشر Core — الفحص مطلوب — الموضع في top-level الوثائق المستندية |
| API طبل المسارات | `/api/resource` + `/api/method` | v2 APIs `/api/v2/*` وأسماء مسارات ديتی تراعى في `before_request` بالإضافة إلى الإضافات |
| DocType jump أعمدة | `module_icon` حذف | مستمر: دوماً افحص أسماء الأعمدة الفعلية قبل `get_all(fields=[...])` |

**الخطة الوقائية الافتراضية عند التخريب v16**: تحديد `MODULE_CONTROL["enabled"] = False` — الطرح بأمان (تعطيل بحيث لا يُخرب الواجهة) بالتعديل الأولي في `config.py` قبل بعض الترقية — الشرّح في ROLLBACK.

## 5. بعد التحديث

- تنفيذ الاختبارات الآلية (الأمر في TESTING) — كلها 7/8 ok (متاسّا 1 حسب الإعداد).
- اجعل التغييرات التالية في config.py يدوياً بعد التحقق (القواعد الإجبارية لا تُكتب تلقائياً أثناء الترقية).

## 6. نصائح عميلة منفذة في بيئتنا

- لو انهار migrate بسبب `before_tests` (تطبيقات أخرى مثل lending): تشغيل السكرتبت المباشر للاختبار (TESTING §1).
- في حال ظهور مشاكل إن أضيفت workspaces جديدة بعد الترقية: المزامنة التلقائية عبر `run_sync` تلتقطها عند أول migrate.
