# ROLLBACK — التراجع/الإيقاف دون فقد بيانات

هذا الدليل يوثق طرقاً **منفذة فعلياً** أثناء التحقق على الموقع، مع ملفات النسخ الاحتياطية الجاهزة (`/home/newsmart/backups_mc/`).

## 1. إلغاء الإخفاء لكل القواعد (بدون إلغاء تثبيت النظام) — منفذ

من داخل خارطة الإدارة (`/app/module-control-settings`):

- اضبط مسودة قواعد فارغة ثم **طبّق التغييرات**، أو استخدم **استرجاع الافتراضي**.
نتيجة فعلية (جولة Projects):
- `applied_flags.hidden_modules = []`، `blocked_modules = []`
- boot sidebar: 53 مجember مع عودة Projects
- `/api/resource/Project` رجعت **200**
- التنقل المباشر `/app/projects` فتح مجدداً (عنوان «المشاريع»)

بـ API (مثل operator نافذة Console):

```javascript
await frappe.xcall('custom_erp.custom_app.module_control.api.save_and_apply',
  { payload: JSON.stringify({ rules: [], workspace_rules: [] }) });
```

## 2. إلغاء النظام كاملاً مؤقتاً

**خيار (أ) من الواجهة**: أطفئ «تفعيل التحكم المركزي» + قم بـ `Apply` → كل التصفية تختفي في الطلبات الجديدة.

**خيار (ب) أخطر من Python** (يظل مفروضاً على الواجهة):
```python
# module_control/config.py
MODULE_CONTROL = {"enabled": False, ...}
```
ثم الديل المعرّف في INSTALLATION (سكربت مباشر) أو إعادة تشغيل workers؛ لكن ملاحظة مهمة: هذا يعطل نهائياً النظام بغض النظر عن الـ UI (حتى الأزرار في الواجهة المستحيلة للتعديل).

## 3. إلغاء hooks من التطبيق (الوجوة)

1. **نسخ احتياطي مسبق موجود**:
   - `/home/newsmart/backups_mc/hooks.py.bak` — نسخة `hooks.py` الأصلية **قبل الدمج**.
2. لكن **الاستبدال الكامل للملف** غير مفضل؛ إذا كانت هناك تعديلات لاحقة على الـ hooks (لاحقاً في custom_erp أو تطبيقات أخرى) فيُفضّل إزالة الكتل السفلية فقط كما في الخطوة (أ):

أ) إزالة كتل الإضافات التالية فقط من `apps/custom_erp/custom_erp/hooks.py` (القسم السفلي المضمن بعنوان `Central Module Control Manager`):

- `doc_events.update(...)` (القسم الأول فقط — الأزواج المكثفة for Module Def / Workspace)
- `after_install`، `after_migrate +=`، `before_request`، `boot_session`
- `has_permission.update({"*": ...})` و`permission_query_conditions.update({"*": ...})`
- `override_whitelisted_methods = {...}`
- `app_include_js +=` و`app_include_css +=` (سطرا الأصول فقط)
- Android pour `from custom_erp.custom_app.module_control.workspace_filter import ensure_desktop_patched` try/except

ب) ثم:
```bash
bench --site site1.local clear-cache
# في نسخة الإنتاج: bench restart / supervisorctl restart
```

**النتيجة الفعلية للك отмен**: ال DocTypes والقواعد وAudit Log تبقى في قاعدة البيانات — التصفية والحظر يختفيان نسبتاً، وbyte مقابل انتهى النظام من السحب العاوم (يعمل مع كل الإبيقيتين).

## 4. إزالة DocTypes وسجلات النظام (اختياري — فقط عند التأكد من عدم الحاجة للإعدادات)

```bash
cd /home/newsmart/frappe-bench2 && env/bin/python - <<'EOF'
import frappe
frappe.init(site="site1.local", sites_path="sites"); frappe.connect()
for d in ("Module Control Settings","Module Control Rule","Workspace Control Rule","Module Control Audit Log"):
    if frappe.db.exists("DocType", d):
        print("removing doctype:", d)
        frappe.delete_doc("DocType", d, ignore_on_trash=True)
frappe.db.commit(); frappe.destroy()
EOF
bench --site site1.local clear-cache
```
> **تنبيه**: هذا الخيار يزيل بيانات الإعدادات وقواعدها وسجل التدقيق نهائياً. الخيار المفضل دائماً: §3 (إزالة الـ hooks فقط) مع الاحتفاظ بالـ DocTypes كأرشيف.

## 5. مذيّلات الفشل بعد التراجع (خطوات يجب أن تراها جميعها)

| الفحص | التوقع |
|---|---|
| `/app` boot: `allowed_workspaces` يبقي 53 منهم Projects | ✅ |
| `/app/projects` يفتح مباشرة بعنوانه | ✅ (منفذ) |
| `/api/resource/Project` → GET/POST | 200 indel (منفذ GET) |
| sidebar وعرض المساحات | الحالة الأصلية السابقة على التفعيل |

## 6. النظام الحقيقي للاستعادة الدقيقة من backips

```bash
# 1. نسخة الحالة من snapshot (json) — من داخل الدسكتوب:
await frappe.xcall('custom_erp.custom_app.module_control.api.export_config')
# ... احفظ hash (state snapshot export)
# 2. أستعادة المؤتمر ل DB (المستوى الج)
bench --site site1.local restore /path/to/backup.sql.gz   # يحفر بالضرورة أن تسقط مجموعة التحديث بين مؤثر
```

**لا تُستبعد أتص الملفتين إلا بح teammates بينهما المعرفة — اطلب فقط من مدير النظام أو من الدازا في المراجع التالية الإصدار الج.closest.**
