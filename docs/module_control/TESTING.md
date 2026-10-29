# TESTING — الاختبارات: الأوامر والنتائج **المنفذة فعلياً**

> كل نتيجة أدناه نُفذت على الخادم `192.168.0.248 / site1.local` بتاريخ 2026-10-28 (رقم التسلسل في السجل متوفر في `Module Control Audit Log`). أي بند لم يُنفذ سيوضح صراحة.

## 1. حزمة الاختبارات الآلية — `test_module_control.py`

يحتوي 8 اختبارات على `FrappeTestCase` (تستعيد الحالة الأصلية للإعدادات في `tearDownClass` — آمنة على الإنتاج).

**كيف نُشغّلت فعلياً:** أمر `bench run-tests` انكسر بوحة hook من تطبيق آخر (`lending.test_utils.before_tests` يطلب `_Test Company` وهو غير موجود بالموقع)، فنُفّذ الإغلاق عبر سكربت مباشر:

```bash
cd /home/newsmart/frappe-bench2 && env/bin/python /tmp/tmp_runtests.py
# (سكربت: frappe.init + unittest.TextTestRunner on TestModuleControl)
```
النتيجة الفعلية (قبل إصلاح خطأ test-العكس ثم بعده):

```text
Ran 8 tests in 8.188s
OK (skipped=1)
RESULTS: run=8 errors=0 failures=0 skipped=1
```

| الاختبار | النتيجة |
|---|---|
| test_hide_module_state_effective | **ok** |
| test_workspace_rule_hide_single | **ok** |
| test_blocking_generates_doctype_list | **ok** |
| test_py_forced_rules_persist_after_ui_unlock_attempt | **skipped** (لا قواعد Python-Forced في config.py — الحالة الافتراضية) |
| test_unhide_returns_module_to_visible | **ok** |
| test_disabled_rule_has_no_effect | **ok** |
| test_admin_access_blocking_core_bypass_documented | **ok** |
| test_query_conditions_hook_blocks_doctype | **ok** (بعد تعديل الاختبار لجلسة غير Administrator) |

## 2. الاختبارات الحيّة (Live) المنفذة عبر HTTP/المتصفح — جولة Projects

### اختبارات الإخفاء (تمت جميعها بنجاح)

| # | سيناريو | النتيجة |
|---|---|---|
| L1 | إخفاء موديول لمستخدم SYSTEM MANAGER (boot:52بدون+sidebar) | ✅ |
| L2 | إخفاء موديول Workspace Manager (moneerali:67بدون) | ✅ |
| L3 | إخفاء موديول Administrator (67بدون) | ✅ |
| L4 | إخفاء مساحة واحدة فقط، بقية الموديولات تبقى | ✅ (sidebar 53 مع عودتها بعد الإسترجاع) |
| L5 | إخفاء كل مساحات الموديول | ✅ |
| L6 | التنقل المباشر للمساحة المخفية `/app/projects` | ✅ «الصفحة projects غير موجود» |
| L7 | التنقل المباشر حسب get_desktop_page (API) للمخفية | ✅ 403 عربية |
| L8 | عودة إظهار Workspace بعد إزالة الحظر (rollback) | ✅ 53 مساحة وreturn إلى 200 |

### اختبارات الوصول (تمت جميعها بنجاح — بجلسة smartqa)

| # | سيناريو | النتيجة |
|---|---|---|
| A1 | فتح رابط DocType مباشرة (`frappe.client.get / S-PROJ-0001`) | ✅ 403 |
| A2 | فتح مسار Workspace المخفي (xcall مثل router) | ✅ حظر (403) |
| A3 | تشغيل Report مرتبط بالموديول (`Project Summary`) | ✅ 403 «ليس هناك إذن لقراءة مشروع» |
| A4 | تنفيذ API قراءة (`GET /api/resource/Project`) | ✅ 403 |
| A5 | تنفيذ API قراءة مستند (`GET /api/resource/Project/{name}`) | ✅ 403 |
| A6 | تنفيذ API إنشاء (`POST /api/resource/Project`) | ✅ 403 |
| A7 | تنفيذ إنشاء عبر `frappe.client.insert` | ✅ 403 |
| A8 | تنفيذ إنشاء عبر Python (`get_doc(...).insert()`) | ✅ PermissionError |
| A9 | قوائم المكشوفة (`frappe.client.get_list` → موديول Projects المكون من Task/Timesheet/…) | ✅ 200 [] (غير مرئية) |
| A10 | API حذف — **لم يُنفذ منفرداً** (المسار نفسه `/api/resource` منطبع في A5؛ حذف عبر RPC يتطلب doc موجود ويرفض بالتosition نفسها) | لم يُنفذ كاختبار مستقل |
| A11 | الفرق POST-CREATE للمستخدم Administrator — **يتجاوز** (Core) موثقة | ✅ سُجّلت كما هي (لا ادّعاء منع) |
| A12 | حظر مسارات method عند `block_protected_apis` (`/api/method/erpnext.*` 403 و`/api/method/frappe.*` 200) | ✅ |

### اختبارات الاستقرار

| # | سيناريو | النتيجة |
|---|---|---|
| S1 | استمرارية مساحات غير مستهدفة (Accounting وغيرها) أثناء الإخفاء | ✅ تعمل وتفتح |
| S2 | عدم تسرّب الكاش بين الجلسات (version-keyed state) | ✅ (tchanging apply → version bump → refresh) |
| S3 | `bench migrate` أثناء النظام | ✅ نجاح مرتين (بعد ال docTypes، وبعد الجولة الأولى للتعديل) — `after_migrate sync` طبق |
| S4 | عدم تعطيل واجهات few Frappe düzen (boot/side/theme) | ✅ — فشل الواجهة كالسيف التالك الحقيقية |
| S5 | تشغيل عدة تطبيقات الأخرى (apps.py get_apps) بعد الدر مش | ✅ (no crash: sidebar filtered) |
| S6 | إمكانية عمل موقف الإصرار (Workspace Manager ليس بإمكانه رؤية المخفية) | ✅ (L2) |

## 3. النتائج التي تثبت الحدود (مثبتة بلا تجميل)

- Administrator لديه core bypass على حظر الوصول (`has_permission` ترجع True قبل hooks) — موثّق.
- `frappe.get_all(ignore_permissions=True)` أرجع 1 Project أثناء الحظر — موثّق (فجوة core موثقة في PERMS doc).

## 4. إطار الممارسة للتوسم المستمر (مستقبلاً — غير منفذ)

- دمج ضمن CI مع `bench run-tests --app custom_erp` بعد عزل التطبيقات المخالفة أو الـ seed of `_Test Company`.
- اختبارات تعدد الـ workers/الجداول المجدولة (schedule & workers) كعمليات مراقبة أثناء التشغيل لا أثناء التثبيت.
