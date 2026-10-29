# PERMISSIONS_AND_SECURITY — الأمن: ما يُحظر، وما لا يُحظر

> **قاعدة النظام**: نُميّز بوضوح بين (أ) إخفاء بصري — لجميع المستخدمين، و(ب) حظر وصول فعلي — على مستوى الخادم للقواعد المفعّلة. **لا نجعل الإخفاء البصري بديلاً عن الأمان.**

## 1. إخفاء الواجهة البصري — ما تم التحقق منه فعلياً

جولة الاختبار على موديول **Projects** في الموقع `site1.local`:

| المستخدم | مجموعة الدكرت | SIDEBAR قبل | SIDEBAR بعد الإخفاء | `frappe.boot.allowed_workspaces` |
|---|---|---|---|---|
| smartqa@example.com | 49 دور (System Manager) | 53 مساحة | **52 ولا Projects** ✅ | no `projects` ✅ |
| Administrator | 117 دور (incl. Workspace Mgr) | 67 صفحة | **67 صفحة ولا Projects** ✅ | — |
| moneerali@gmail.com (Workspace Manager) | 57 دور | 67 | **67 ولا Projects** ✅ | — |

أسطح الفحص:** `/app` boot، HTTP `get_workspace_sidebar_items` (200، 52/67 بدون Projects)، التنقل المباشر `/app/projects` («الصفحة projects غير موجود»)، API `get_desktop_page` للمساحة المخفية (403: «مساحة العمل Projects غير متاحة»)، مع بقاء كل مساحة مرئية (Accounting) تعمل كالمعتاد.

## 2. حظر الوصول الفعلي — تغطيتها الفعلية (لGORITHM المسوض الأمني)

| قناة | نتيجة الاختبار (smartqa، حظر Projects مفعّل) |
|---|---|
| `GET /api/resource/Project` | **403** (حظِر على مساره، بالعربية) ✅ |
| `GET /api/resource/Project/S-PROJ-0001` | **403** ✅ |
| `POST /api/resource/Project` (إنشاء) | **403** ✅ |
| `frappe.client.get` (المسار المسؤول لفتح النموذج) | **403** ✅ |
| `frappe.client.get_list` | **200** لكن `[]` (غير مرئ battered) ✅ |
| `frappe.client.insert` (إنشاء) | **403** ✅ |
| قائمة `Task` / `Timesheet` (موديول نفسه) | **200** `[]` — غير مرئypsum ✅ |
| تشغيل تقرير `Project Summary` (مرجع Project) | **403: «ليس هناك إذن لقراءة مشروع»** ✅ |
| `frappe.set_user("smartqa")` → `has_permission(doc.read)` | False ✅ |
| **إنشاء عبر get_doc + insert (Python)** | **PermissionError** ✅ |
| قاعدة `block_protected_apis=1` | `/api/method/erpnext.*` **403**، `/api/method/frappe.*` **200** ✅ |

## 3. الحدود المعروفة (موثقة، مهم جداً)

### أ. Administrator: التباس Core (بعكس الإخفاء البصري)
`frappe/permissions.py:94-96`: عند `user == "Administrator"` ترجع الدالة `True` **قبل** الـ hooks.
التحقق الفعلي أثناء الحظر العملي: `ADMIN has_permission(Project read): True`, `create: True`.
**لا تصحح الـ Core** — هذا السلوك جزء من أمان Frappe (التقليل يُكسر النظام). إذا احتجت عزلاً حقيقياً عن Administrator: فصل DB/إذن driver بالحلول المترتبة على مستوى البيانات.

### ب. `frappe.get_all(ignore_permissions=True)` والـ SQL المباشر
**التحقق الفعلي أثناء الحظر**: `get_all("Project")` أرجع 1 صف — سلوك نواة Frappe، إذ `get_all` يبتغير `ignore_permissions=True` افتراضياً ولا يمر عبر `permission_query_conditions` ثم لا يستجيب للغة القفل — ال jaws المكتملة `get_list` / الـ UI / REST. أي كود خادم أو SQL يدوي لن يُحظر.

### ج. مسارات الأكواد التي لا تغطيها القبعات
- مجدولة (`Scheduler`) تؤدي العمليات باسم مستخدميها ( أسهل وضعاً من بقايا).
- تقارير «أنواع» منسوجة من الـ Report Builder بلا بيانات مُثِّلَت.
- خضوع الـ API في Frappe v15: `/api/resource` و`/api/method` و`/api/query` آخروا (بطاقة API v2) - Query-Snippet...
- أي code path لا تراقب `frappe.permissions.has_permission` أو DB-Query — للموديول المختار قد يمنحه المال للتنفيذ مستورد الأوامر تُطلق على الأخرة (مثالladı: imports/excel).

### د. ما لا يقيه مستوى DocType الوحيد
- DocTypes؟ `Page` / `Report` / `Dashboard` الخاصة بالموديول: تمّت تغطية يدوية بالـ state (block pages/reports للالمكاترب) لكنها ليست instance-level كل مسار belongs له — مخصص مسبقاً على pairs الموثوقة.
- مسار تحمّل/رفع الصور التفصيلي:
  - `高楼 استхранال لا يفرش` (من `EXCLUDED_DOCTYPES`) — يبقى متاحاً للـ UI.

## 4. فهم المستندات التي تتأثر بجوائز حظرها من الـ Workspace

- `Workspace` المقيّد بالاسم الداخلي: حُظر الوصول عبر `get_desktop_page` — حتى لـ Workspace Manager — التحقق فعلي: xcall على workspace `Projects` أرجع 403.
- الأنماط الأخرى للـ workspace (hidden × private...): تمت التغطية بنفس الأسلوب المحتوى of (list after index).

## 5. pratice أفضل الممارسات

1. عند الحصول على **لهجة أمنية حقيقية** — إضف تطبيق الموارد المتغيرة حسبervers يجب أن تكون للخبراء في المستوى DB (المستخدمة إدناف عثرة).
2. كل حماية صنعناها **فضية في ملف الموثء** (`PERMISSIONS_AND_SECURITY.md` هذا) — لأي نغم الحفظ في محطة أمثلة الأمان من REGENT عاخر للمستخدم.
3. عندما کسب العضو على مسار مُطأحق، التبسيط تنتعلم مسارłe API-casting V2 غير المりました في هذا doc — تفتح على_HELPER في CONFIGURATION (`protected_api_scope`).
