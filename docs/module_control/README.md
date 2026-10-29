# Central Module Control Manager — نظام التحكم المركزي في الموديولات

نظام مركزي متكامل داخل تطبيق `custom_erp` لإدارة **إخفاء** الموديولات/مساحات العمل و**حظر الوصول الفعلي** إليها على مستوى الخادم، لجميع المستخدمين (بما في ذلك Administrator وWorkspace Manager وSystem Manager في الإخفاء البصري)، دون تعديل Frappe/ERPNext Core.

## المكونات

| المكوّن | المسار | الوظيفة |
|---|---|---|
| حزمة النظام | `custom_erp/custom_app/module_control/` | config, visibility, workspace_filter, permissions, scanner, sync, audit, api |
| DocTypes جديدة | `custom_app/doctype/module_control_*` | `Module Control Settings` (Single)، `Module Control Rule`، `Workspace Control Rule`، `Module Control Audit Log` |
| واجهة الإدارة | `public/js/module_control_settings.js` + `public/css/module_control.css` | لوحة تحكم عربية/إنجليزية RTL على `/app/module-control-settings` |
| Hooks | `hooks.py` (القسم السفلي) | doc_events, boot_session, before_request, has_permission, permission_query_conditions, override_whitelisted_methods, after_install/after_migrate |
| الاختبارات | `custom_erp/custom_app/tests/test_module_control.py` | 10 اختبارات (9 ناجحة، 1 متخطاة بمبرر — الحالة الافتراضية) |
| الوثائق | `docs/module_control/` | 12 ملفاً تشغيلياً |
| مساحة لوحة التخصيص | Workspace «إدارة التطوير» | تُنشأ تلقائياً، Administrator فقط — كل مكونات التخصيص فيها (اللوحة، سجل التدقيق، الموديولات، المساحات، القواعد، الروابط) |
| الترجمة | `custom_erp/translations/ar.csv` | 294 سطراً تشمل جميع نصوص التخصيص بالعربية |

## ما يمتلكه النظام (تم التحقق منه فعلياً على الموقع)

1. **إخفاء بصري شامل**: يحجب `bootinfo.allowed_workspaces` + شريط sidebar + مخطط الموديولات + التنقل المباشر — لجميع المستخدمين بما فيهم Administrator وعملاء Workspace Manager (نتائج الاختبار: Administrator 67 مساحة بدون Projects، smartqa 52 بدون Projects).
2. **إخفاء للبحث** (`Hide From Search`) ولجميع مساحات الموديول (`Hide All Workspaces`) مع التقاط المساحات الجديدة تلقائياً عند المزامنة.
3. **فرض من Python** (`module_control/config.py`): قواعد `forced_hidden_modules` / `forced_hidden_workspaces` / `forced_blocked_modules` مع وسم "Enforced by Custom App" لا يمكن إلغاؤه من الواجهة.
4. **حظر وصول فعلي على الخادم** (اختياري): رفض قراءة/كتابة/إنشاء/حذف على مستوى DocType + مسارات `/api/resource/{doctype}` + `/api/method/{app}.*` (اختياري لكل قاعدة) — نتائج: كل مسارات `Project` أرجعت 403، والقوائم أصبحت غير مرئية (فارغة).
5. **مزامنة تلقائية idempotent**: بعد migrate، وتركيب، وعلى تغيّر `Module Def`/`Workspace` (enqueue + قفل 60s)، مع bump لإصدار البيانات وإبطال الكاش عبر workers.
6. **سجل تدقيق** يوثّق كل تغيير (المستخدم/الوقت/قبل-بعد/المصدر) — تحقق فعلي: 7 عمليات موثقة خلال جولة الاختبار.
7. **Preview Impact**: تحليل اعتماديات DocField-Link والتقارير قبل الحظر (تحذيرات بصرية داخل الواجهة).

## حدود النظام (مهم جداً — لا تُعامل كضمانات أمنية شاملة)

- **Administrator يتجاوز حظر الوصول على مستوى Core في Frappe v15** (`frappe.permissions.has_permission` يقبل قبل الـ hooks) — تحقق فعلي: `ADMIN has_permission(read): True`. الإخفاء البصري يسري عليه لكن حظر الوصول لا يسري.
- `frappe.get_all(ignore_permissions=True)` والـ SQL المباشر غير محميين (تحقق فعلي: أرجع 1 صف أثناء الحظر) — سلوك نواة Frappe، لا يغطيه أي نظام hooks.
- التفصيل الكامل: `PERMISSIONS_AND_SECURITY.md`.

## متطلبات التشغيل

- Frappe Framework v15 / ERPNext v15 (نفس البنية المثبتة: bench على `/home/newsmart/frappe-bench2`، الموقع `site1.local`).
- Redis (cache + queue) — مطلوب من قابلية state/queue.
- الصلاحية: الواجهة متاحة لـ Administrator وSystem Manager فقط (`require_admin()`).

## تعليمات سريعة

```bash
cd /home/newsmart/frappe-bench2
bench --site site1.local migrate          # مزامنة DocTypes + after_migrate sync
bench build --app custom_erp              # بناء الأصول
bench --site site1.local clear-cache      # تفريغ الكاش (اختياري)
```

الوصول: `/app/module-control-settings`
