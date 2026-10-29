# TROUBLESHOOTING — الأخطاء والمجاري الحل الحقيقي

كل بنصر أدناه بدأ الخطأ وتم تصلح فعالياً أثناء إنجاز النظام في هذه البيئة (Frappe v15 مثبَّت).

## 1) `bench execute` يفشل: `NameError: custom_erp is not defined`

**السبب**: مسار `frappe/commands/utils.py:272` يعيد `eval(method + "(*args, **kwargs)", globals(), locals())` — eval على وحدات تطبيقات مخصَّصة يفشل.
**الحل المجرّب**: سكربت بايثون المباشر:
```bash
cd /home/newsmart/frappe-bench2
/home/newsmart/frappe-bench2/env/bin/python /tmp/<script>.py   # يشمل frappe.init + frappe.connect
```
مهم: شغّل من داخل مجلد الـbench (وإلا فشل logging: `FileNotFoundError: /home/logs/database.log`).

## 2) خطأ `Unknown column 'module_icon' in 'SELECT'`

**السبب**: بعض نسخ v15 المثبتة لا تحتوي عمود `module_icon` في `tabModule Def`.
**الح真正做到**: إزالة العمود من `scanner.get_module_inventory` — تم، والـ API 200 مع 59 موديول.

## 3) `frappe.get_all(pluck=)` يرجع strings، والكود ينتظر objects

**الخطأ الفعلي**: `AttributeError: 'str' object has no attribute 'name'`.
**الحل**:
```python
existing_modules = set(frappe.get_all("Module Def", pluck="name"))
```

## 4) فشل `override_whitelisted_methods` عند عدم وجود `@frappe.whitelist()` على الدوال البديلة

**الخطأ الفعلي (403)**: `Function custom_erp...get_desktop_page_filtered is not whitelisted.`
**المسبّب**: دوال الاستبدال يجب التعليم عليها `@frappe.whitelist()`.
**الحل**: أضفنا `@frappe.whitelist()` على `get_workspace_sidebar_items_filtered` و`get_desktop_page_filtered` (النموذج موثق في DEVELOPER_GUIDE).

## 5) خطأ `get_workspace_sidebar_items() got an unexpected keyword argument 'cmd'`

**السبب**: `frappe.call` (client) يحقن `cmd` و `lang` في الـ HTTP args.
**الحل**: `kwargs.pop("cmd", None); kwargs.pop("lang", None)` قبل التفويض في دوال الاستبدال.

## 6) فشل التفريق بين شكل `page` مرسال من الـ UI (object vs string)

- `page` داخل الـ UI تمرّ أحياناً **كسلسلة JSON** — والغلاف يجب أن يدعم الشكلين: إن وصل الـ dict إلى الدالة الأصلية فتفشل `json.loads(dict)` بـ `TypeError: the JSON object must be str, bytes or bytearray, not dict`.
- **الحل**: الغلاف `wrap_get_desktop_page` يفحص الشكلين: للسلسلة (`str`/`bytes`) يعمل `_json.loads` للفحص فقط ثم يستدعي الأصل بالوسيطة الأصلية، وللكائن (`dict`) يفحص مباشرة — النتيجة المُتحقق منها: Accounting 200 / Projects 403.

## 7) `AttributeError: module 'frappe.utils' has no attribute 'unescape_html'`

**السبب**: الدالة غير موجودة في v15 المثبت.
**الحل**: `urllib.parse.unquote` (المكتبة القياسية) في `before_request_hook` لقراءة أسماء DocTypes من مسار `/api/resource/`.

## 8) بداية الـ Worker (وظيفة restart متأقلة)

- **بيئة التشغيل**: `bench serve` مع werkzeug reloader يقرأ التغييرات ~8 ثوانٍ بعد رفع الملف (لا حاجة إلى manual restart). للاستخدام الإنتاجي (gunicorn): `bench setup supervisor` — **لم يُختبر في هذه البيئة**.
- بعد تعديل `*.py` المسار الأول فقط؛ تعديل JS/CSS يلزم: `bench build --app custom_erp`.

## 9) الـ settings الصفحة لا تعرض القواعد (الإعداد الأول)

إن كانت `enabled=0` والـ `last_synchronization` يساوي None: نظام أول sync سيعبّئ الـ defaults تلقائياً (`initialized_defaults: True`). إن لم يحدث: نفّذ **مزامنة (Sync)** من الواجهة.

## 10) التصفيّة لا تظهر بعد التطبيق

تأكد من الخطوات بالترتيّب:
1. لديك جلسة `System Manager` أو Administrator.
2. `enable_global_workspace_filter = 1` (المقابل للفرض في config).
3. زر **طبّق التغييرات** (رقم الإصدار version يرتفع — والشريط يعرضه).
4. `bench --site <site> clear-cache` (تلاعب أثر تصميمي: يعمل معقولاً على متعدد workers).

## 11) الحظر لا يمنع كل مسار API (method scope)

- في القاعدة المسجّلة: `block_protected_apis = 1` لتفعيل حظر مسارات method لإدارة التطبيق.
- تنبيه: `protected_api_scope="app"` يمنع كل `/api/method/{app_name}.*` لتطبيق الموديول المحظور (مثال: حظر `Projects` مع العلم المفعّل يحجب كل API الخاص بـ ERPNext؛ استخدمها فقط للقضية المحددة، أو اجعل `scope = "none"` وتعتمد على حظر `/api/resource` فقط — والحماية الأوسع على مستوى الوكيل/CDN تُدار خارج النظام).

## 12) تسجيل الأخطاء

- `sites/site1.local/logs/module_control.log` — أخطاء الأغلفة/الحظر (بتسلسل موثق).
- `sites/site1.local/logs/module_control_audit.log` — failures سجل التدقيق.
- UI «عُدّة الفحص» من جانب التطبيق: `custom_erp.custom_app.module_control.api.get_overview` (HTTP 200 + 59 modules).
