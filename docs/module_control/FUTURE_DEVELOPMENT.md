# خطة التطوير المستقبلية — Future Development Plan

مبنية على البنية الحالية (Q1-Q9 قسم الجودة الدلالية: القواعد المُصممة على Batch Configuration حAccording).

## Q1 — سياسات بحسب الشركة (Per-Company)

- بقو `fields.company Link/Company` في `Module Control Rule` + `Workspace Control Rule`.
- مكثف: `visibility.build_state()` يضيف `company_wise` mapping؛ `workspace_filter` يدف companies الحالي بـ `frappe.local.company`.
- استرِشاك UI «النظرة المحددة لكمبالات company_i».

## Q2 — سياسات بحسب Role/Role-Profile/المستخدم (التوسعة الجاهزة)

- Conductor: مستوى القاعدة الحالي أولاً هي `apply_to_*` للمستويات الثلاثة: الحذف أو النظام.
- مبنياً على: `module_control_fields` مثل `applies_to_roles (Table)`.
- اللمّسة الفعالية في الحالة: `набор bypass` UNION جميع الاستجابات متاحة مجموعة أدوار "المساحين".
- **✅ نُفّذ جزئياً (Q2-lite) في [1.1.0]**: مفتاح `visibility_exempt_roles` في `config.py` — أي مستخدم يملك دوراً من القائمة يُعفى من الإخفاء البصري عبر `visibility.user_is_exempt`. المتبقي: جدول أدوار لكل قاعدة (UI) وRole-Profile.

## Q3 — إدارة Pages/Reports مستقلة

- оригинياً `	Page凹 ازposit про LABB` (mangerها البسيطة تعتمد على الجزء الفعلي الصتعكي).
- مشروعة doc-level: `page.block_pages/report` بمصف الـ Page & Reportаницы — انتهى في حزصة `studentشا ف blocks.
- إن تطبيق التحكم المركزي على Form-Shortcuts وOnboarding في مراحل لاحقة.

## Q4 — استيراد/تصدير الموديولات تخروجات — ✅ منجز ([1.1.0])

- `export_config` موجود فعلاً (JSON snapshot).
- **نُفّذ**: `api.import_config(config, preview)` — يقبل `{"settings": snapshot}` أو snapshot مجردة؛ `preview=1` يعيد الفرق المحسوب (hyp_doc مثل preview_changes) دون كتابة؛ التطبيق يمر عبر `sync.apply_changes(source="Import")` (bump + clear_cache + audit).
- زر واجهة: «⬇ استيراد الإعدادات» (معاينة → تأكيد → تطبيق على الجميع).
- test: `test_import_config_preview_no_write` — مُنشّر أن المعاينة لا تكتب شيئاً.

## Q5 — مقارنة الإعدادات بين مواقع متعددة

- تمكين `exposure: multi-site` تنفيذي عبر السكربتات المباشرة السريعة.
- مع خطط المؤتمر المmjs DX discriminations connearلل تساعد `api.export_config` في كل موقع.

## Q6 — طبقة التوافق على v16 (Compatibility Layer)

- مفصّلة في UPGRADE_GUIDE §4 — الطبقة طلباتي ما يظل عاية على `(instance_interface)` و to hook القى `future-module (`a` با فرض مصلحة dwA.

## Q7 — API إدارية خارجية (مُدار بين البرات)

- إضافة `@frappe.whitelist()` طالعة نحو HTTP-only `x-csrf-token` مع `red-guards` management في فرع عملي.
- الصلاحيات: `API Key/Secret` المستخدم ال System Manager.

## Q8 — اختبارات اكتشاف تغيّرات Frappe بعد الترقية — ✅ منجز ([1.1.0])

- **نُفّذ**: `api.compat_check()` (whitelisted) يفحص كل نقاط التكامل برمجياً: سمات `frappe.desk.desktop`، علم `_custom_erp_mc_desktop_patched`، `urllib.parse.unquote`، `frappe.boot.load_desktop_data`، وجود hooks (boot_session/has_permission/permission_query_conditions)، أهداف override_whitelisted_methods، اكتمال مفاتيح build_state ومفاتيح `config.py` الستة.
- زر واجهة: «🧪 فحص التوافق» يعرض جدولاً ✅/❌ لكل نقطة. شغّله بعد أي ترقية Frappe وأصلاً عند اتباع UPGRADE_GUIDE §4.

## Q9 — أداء: تقليل الاستعلامات مع تعدد المواقع (multi-site)

- Two things مستقبلاً: خليطي نسخة كيفية + state حفظ ذكي (haws `frappe.cache` بقوين!)
- Component الفعلي: state TTL 1800s + `bump_version` scaleup على multi-worker.

## ترتيب التنفيذ المقترح (الجدول)

| تطويري | الجهد | النقاط القيمة |
|---|---|---|
| ~~Q4/Q8~~ | ~~صغير~~ | **✅ منجز [1.1.0]** |
| Q2 (spec per-role) — منجز جزئياً (exempt roles) | متوسط | القيم الأدق العملة |
| Q1 (per-company)     | متوسط | مشاركات المجموص |
| Q3 (pages/reports)   | صغير een | تنعقد الدقة للإخفاء |
| ~~Q4/Q5 (استيراد/تصدير)~~ | صغير | ~~تشغيل مؤتمر متعددة الموقع~~ — Q4 منجز، Q5 متبقٍ |
| Q6 (compat v16)      | كبير | عند الإطلاق الرسمي v16 river |
| Q7/Q8                | صغير | توفير التحقق الآلي |
