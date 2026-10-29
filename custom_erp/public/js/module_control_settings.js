/**
 * Central Module Control Manager — Admin UI (Module Control Settings)
 * مركز التحكم الكامل في إخفاء/حظر/تفعيل الموديولات والمساحات.
 * يدعم: البحث، التصفية، الجمعي، Preview Impact، سجل التدقيق، واجهة RTL/Arabic.
 */
const MC = {
	overlay: null,
	data: null,
	draft: null, // {rules:{module:{...}}, workspaces:{name:{hide, block_nav}}}
	filter: "all",
	search: "",
	_timer: null,
	urls: {
		overview: "custom_erp.custom_app.module_control.api.get_overview",
		sync: "custom_erp.custom_app.module_control.api.sync_now",
		scan: "custom_erp.custom_app.module_control.api.scan_modules",
		impact: "custom_erp.custom_app.module_control.api.get_module_impact",
		preview: "custom_erp.custom_app.module_control.api.preview_changes",
		apply: "custom_erp.custom_app.module_control.api.save_and_apply",
		restore: "custom_erp.custom_app.module_control.api.restore_defaults",
		import: "custom_erp.custom_app.module_control.api.import_config",
		compat: "custom_erp.custom_app.module_control.api.compat_check",
	},
};

frappe.ui.form.on("Module Control Settings", {
	refresh(frm) {
		setTimeout(() => MC.init(frm), 220);
	},
});

MC.init = function (frm) {
	if (MC._initialized_frm === frm) {
		if (MC.overlay) MC.overlay.show();
		return;
	}
	MC._initialized_frm = frm;
	MC.frm = frm;

	if (!MC.overlay) {
		$(`<style>
			.mc-chip{display:inline-block;padding:1px 7px;border-radius:9px;font-size:10.5px;margin-inline-start:3px;white-space:nowrap}
			.mc-chip-hide{background:#ffe08a;color:#5b4300;border:1px solid #e8b34a}
			.mc-chip-block{background:#ffc3b8;color:#7a1f10;border:1px solid #d97b66}
			.mc-chip-force{background:#cde9ff;color:#0b4f91;border:1px solid #7db8e8}
			.mc-chip-diff{background:#e5d5ff;color:#4b1289;border:1px solid #b18ae0}
			.mc-chip-ok{background:#d8f5d8;color:#206b20;border:1px solid #95d595}
			.mc-toolbar{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:8px 0 4px}
			.mc-table-wrap{max-height:60vh;overflow:auto;border:1px solid #d7dbe0;border-radius:8px;background:#fff}
			.mc-table{width:100%;border-collapse:collapse;font-size:12.5px}
			.mc-table th{position:sticky;top:0;background:#f6f8fa;z-index:2;text-align:right;padding:7px 9px;border-bottom:2px solid #d0d4d9;font-size:11.5px;color:#414750}
			.mc-table td{padding:6px 9px;border-bottom:1px solid #eef0f3;vertical-align:middle}
			.mc-table tr:hover td{background:#f7faff}
			.mc-count{color:#6a737d;font-size:11px}
			.mc-name{font-weight:600}
			.mc-app-badge{font-size:10px;background:#eef2f6;border:1px solid #d7dbe0;border-radius:7px;padding:0 6px;color:#4b5563;margin-inline-start:5px}
			.row-changed{background:#fbf3ff !important}
			.mc-footer{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;align-items:center}
			.mc-version{color:#8a929a;font-size:11px;margin-inline-start:auto}
		</style>`).appendTo(document.head);
	}

	let $wrap = frm.$wrapper.find("#mc-control-ui");
	if (!$wrap.length) {
		$wrap = $('<div id="mc-control-ui" class="col-lg-12" style="margin-bottom:22px"></div>');
		frm.$wrapper.find(".form-page .row:not(:first)").first().before($wrap);
		if (!frm.$wrapper.find("#mc-control-ui").length) {
			$(frm.layout.wrapper).before($wrap);
		}
	}

	const html = `
	<div class="mc-toolbar">
		<button class="btn btn-sm btn-secondary mc-btn-scan" style="min-width:90px">🔄 فحص (Scan)</button>
		<button class="btn btn-sm btn-secondary mc-btn-sync" style="min-width:90px">⚙اتص (Sync)</button>
		<button class="btn btn-sm btn-primary mc-btn-apply" style="min-width:130px">💾 طبّق التغييرات (Apply)</button>
		<button class="btn btn-sm btn-secondary mc-btn-preview" style="min-width:110px">👁 معاينة الأثر</button>
		<button class="btn btn-sm btn-secondary mc-btn-audit">🧾 سجل التدقيق</button>
		<button class="btn btn-sm btn-danger mc-btn-restore" style="min-width:110px">↩ استرجاع الافتراضي</button>
		<button class="btn btn-sm btn-secondary mc-btn-import">⬇ استيراد الإعدادات</button>
		<button class="btn btn-sm btn-secondary mc-btn-compat">🧪 فحص التوافق</button>
		<span class="mc-search" style="margin-inline-start:auto;display:flex;gap:6px">
			<input class="form-control mc-filter-search" placeholder="بحث بالاسم (عربي/إنجليزي/داخلي)..." style="width:230px">
			<select class="form-control mc-filter-select" style="width:170px">
				<option value="all">جميع الموديولات</option>
				<option value="hidden">المخفية فقط</option>
				<option value="blocked">المحظورة فقط</option>
				<option value="forced">المفروضة (Python)</option>
				<option value="changed">بها تغييرات غير مطبقة</option>
			</select>
		</span>
	</div>
	<div class="mc-table-wrap"><table class="mc-table">
		<thead><tr>
			<th style="width:26px"><input type="checkbox" class="mc-check-all"></th>
			<th style="min-width:180px">الموديول</th>
			<th>عدد (dt/page/rpt/ws)</th>
			<th style="min-width:150px">الحالة</th>
			<th style="width:250px">إجراءات سريعة</th>
		</tr></thead>
		<tbody class="mc-tbody"><tr><td colspan="5">جارٍ التحميل…</td></tr></tbody>
	</table></div>
	<div class="mc-footer">
		<div class="mc-bulk" style="display:none;gap:6px">
			<button class="btn btn-xs btn-secondary mc-bulk-hide">إخفاء المحدد</button>
			<button class="btn btn-xs btn-secondary mc-bulk-unhide">إظهار المحدد</button>
			<button class="btn btn-xs btn-danger mc-bulk-block">حظر المحدد</button>
			<button class="btn btn-xs btn-secondary mc-bulk-unblock">إلغاء حظر المحدد</button>
		</div>
		<span class="mc-version"></span>
	</div>
	`;
	$wrap.html(html);

	// wiring
	$wrap.find(".mc-btn-scan").on("click", () => MC.act_scan());
	$wrap.find(".mc-btn-sync").on("click", () => MC.act_sync());
	$wrap.find(".mc-btn-apply").on("click", () => MC.act_apply());
	$wrap.find(".mc-btn-preview").on("click", () => MC.act_preview(false));
	$wrap.find(".mc-btn-audit").on("click", () => MC.show_audit());
	$wrap.find(".mc-btn-restore").on("click", () => MC.act_restore());
	$wrap.find(".mc-btn-import").on("click", () => MC.act_import());
	$wrap.find(".mc-btn-compat").on("click", () => MC.act_compat());
	$wrap.find(".mc-filter-search").on("input", function () {
		MC.search = this.value.trim().toLowerCase();
		clearTimeout(MC._timer);
		MC._timer = setTimeout(() => MC.render_table(), 220);
	});
	$wrap.find(".mc-filter-select").on("change", function () {
		MC.filter = this.value;
		MC.render_table();
	});
	$wrap.find(".mc-check-all").on("change", function () {
		$wrap.find(".mc-row-check").prop("checked", this.checked).trigger("change");
	});
	const bulk = $wrap.find(".mc-bulk");
	bulk.find(".mc-bulk-hide").on("click", () => MC.bulk("hide"));
	bulk.find(".mc-bulk-unhide").on("click", () => MC.bulk("unhide"));
	bulk.find(".mc-bulk-block").on("click", () => MC.bulk("block"));
	bulk.find(".mc-bulk-unblock").on("click", () => MC.bulk("unblock"));

	frm.add_custom_button(__("لوحة التحكم المركزي"), () => {
		document.querySelector("#mc-control-ui").scrollIntoView({ behavior: "smooth" });
	});

	MC.reload();
};

MC.reload = function (after = null) {
	frappe.call({
		method: MC.urls.overview,
		callback: (r) => {
			MC.data = r.message;
			MC.draft = MC.init_draft();
			MC.render_table();
			MC.render_status();
			if (after) after();
		},
	});
};

MC.init_draft = function () {
	const draft = { rules: {}, workspaces: {} };
	MC.data.modules.forEach((m) => {
		const r = m.rule || {};
		draft.rules[m.module] = {
			is_enabled: m.py_forced || r.is_enabled ? 1 : 0, // py-forced rows are always enabled
			hide_module: m.py_forced ? 1 : (r.hide_module ? 1 : m.hidden ? 1 : 0),
			block_module_access: r.block_module_access ? 1 : 0,
			hide_all_workspaces: (r.hide_all_workspaces ? 1 : (m.hidden && (m.workspace_count || 0) > 0 ? 1 : 0)),
			hide_from_search: r.hide_from_search ? 1 : (m.search_hidden ? 1 : 0),
			block_direct_navigation: r.block_direct_navigation ? 1 : 0,
			block_protected_apis: r.block_protected_apis ? 1 : 0,
			enforced_by: m.py_forced ? "Enforced by Custom App" : (r.enforced_by || ""),
		};
		(m.workspaces || []).forEach((w) => {
			draft.workspaces[w.name] = {
				hide: w.mc_hidden || w.rule_hide ? 1 : 0,
				block_nav: w.mc_hidden ? 1 : 0,
				enforced: w.enforced ? 1 : 0,
				module: m.module,
			};
		});
	});
	return draft;
};

MC.render_status = function () {
	const s = (MC.data && MC.data.applied_flags) || {};
	const el = document.querySelector("#mc-control-ui .mc-version");
	if (el) {
		el.textContent = "إصدار الإعدادات: " + ((MC.data.settings || {}).configuration_version || 0) +
			" | آخر مزامنة: " + ((MC.data.settings || {}).last_synchronization || "") +
			" | مفروض من Python: " + (s.py_forced_hidden || []).concat(s.py_forced_blocked || []).join(", ");
	}
};

MC.chips = function (m) {
	const d = MC.draft.rules[m.module] || {};
	const chips = [];
	const changed_state = MC.is_changed(m.module);
	if (d.hide_module) chips.push('<span class="mc-chip mc-chip-hide">مخفي</span>');
	if (d.block_module_access) chips.push('<span class="mc-chip mc-chip-block">محظور الوصول</span>');
	if (d.hide_all_workspaces) chips.push('<span class="mc-chip mc-chip-hide">مساحاته مخفية</span>');
	if (m.py_forced) chips.push('<span class="mc-chip mc-chip-force">Enforced by Custom App</span>');
	if (changed_state) chips.push('<span class="mc-chip mc-chip-diff">تغييرات غير مطبقة</span>');
	if (!chips.length) chips.push('<span class="mc-chip mc-chip-ok">ظاهر</span>');
	return chips.join(" ");
};

MC.is_changed = function (module) {
	const m = MC.data.modules.find((x) => x.module === module);
	if (!m) return false;
	const d = MC.draft.rules[module] || {};
	const r = m.rule || {};
	const key = (b) => !!b;
	const applied = {
		is_enabled: key(r.is_enabled),
		hide_module: key(r.hide_module),
		block_module_access: key(r.block_module_access),
		hide_all_workspaces: key(r.hide_all_workspaces),
		hide_from_search: key(r.hide_from_search),
		block_direct_navigation: key(r.block_direct_navigation),
		block_protected_apis: key(r.block_protected_apis),
	};
	return ["is_enabled", "hide_module", "block_module_access", "hide_all_workspaces", "hide_from_search", "block_direct_navigation", "block_protected_apis"]
		.some((k) => !!d[k] !== applied[k]);
};

MC.match = function (m) {
	const d = MC.draft.rules[m.module] || {};
	if (MC.search) {
		const hay = (m.module + " " + (m.module_title || "") + " " + (m.app || "")).toLowerCase();
		if (!hay.includes(MC.search)) return false;
	}
	if (MC.filter === "hidden" && !d.hide_module) return false;
	if (MC.filter === "blocked" && !d.block_module_access) return false;
	if (MC.filter === "forced" && !m.py_forced) return false;
	if (MC.filter === "changed" && !MC.is_changed(m.module)) return false;
	return true;
};

MC.render_table = function () {
	const tbody = document.querySelector("#mc-control-ui .mc-tbody");
	if (!tbody || !MC.data) return;
	const rows = [];
	MC.data.modules.forEach((m) => {
		if (!MC.match(m)) return;
		const changed = MC.is_changed(m.module);
		const forced = m.py_forced;
		rows.push(
			`<tr class="${changed ? "row-changed" : ""}" data-module="${esc(m.module)}">
				<td><input type="checkbox" class="mc-row-check" data-module="${esc(m.module)}"></td>
				<td><span class="mc-name">${esc(m.module)}</span><span class="mc-app-badge">${esc(m.app)}</span>
					<div class="mc-count">${esc(m.module_title || "")}</div></td>
				<td><span class="mc-count">dt:${m.doctypes} pg:${m.pages} rpt:${m.reports} ws:${m.workspace_count}</span></td>
				<td>${MC.chips(m)}</td>
				<td>
					<button class="btn btn-xs btn-secondary mc-act-toggle ${d_disabled(forced, "hide_module")}" data-module="${esc(m.module)}" data-act="hide">👁 إخفاء/إظهار</button>
					<button class="btn btn-xs btn-secondary mc-act-toggle ${d_disabled(forced, "block_module_access")}" data-module="${esc(m.module)}" data-act="block">🔒 حظر/فك</button>
					<button class="btn btn-xs btn-secondary mc-act-ws" data-module="${esc(m.module)}">🗂 المساحات (${m.workspace_count})</button>
					<button class="btn btn-xs btn-secondary mc-act-impact" data-module="${esc(m.module)}">⚠ التبعيات</button>
				</td>
			</tr>`
		);
	});
	tbody.innerHTML = rows.length
		? rows.join("")
		: "<tr><td colspan='5' style='color:#8b949e;text-align:center;padding:14px'>لا توجد نتائج مطابقة للبحث/التصفية</td></tr>";

	const $wrap = $wrap_or_body();
	$wrap.find(".mc-act-toggle").off("click").on("click", function () {
		MC.toggle(this.dataset.module, this.dataset.act);
	});
	$wrap.find(".mc-row-check")
		.off("change")
		.on("change", function () {
			const checked = $(document.querySelector("#mc-control-ui")).find(".mc-row-check:checked").length;
			const $bulk = document.querySelector("#mc-control-ui .mc-bulk");
			if ($bulk) $bulk.style.display = checked > 0 ? "flex" : "none";
		});
	$wrap.find(".mc-act-ws").off("click").on("click", function () {
		MC.ws_dialog(this.dataset.module);
	});
	$wrap.find(".mc-act-impact").off("click").on("click", function () {
		const mod = this.dataset.module;
		frappe.call({
			method: MC.urls.impact,
			args: { module: mod },
			callback: (r) => MC.show_impact(mod, r.message),
		});
	});
};

function $wrap_or_body() {
	return $(document.querySelector("#mc-control-ui") || document.body);
}
function d_disabled(forced, act) {
	return forced ? "disabled" : "";
}
function esc(s) {
	const m = document.createElement("span");
	m.textContent = s == null ? "" : String(s);
	return m.innerHTML;
}
function cstr(s) {
	if (s == null) return "";
	let t = String(s);
	// render old→new booleans/colors nicely inside HTML
	if (t === "true" || t === "True" || t === "1") t = "مضبوط ✔";
	else if (t === "false" || t === "False" || t === "0") t = "مطفأ ✘";
	return t;
}

MC.toggle = function (module, act) {
	const forced = MC.data.modules.find((x) => x.module === module)?.py_forced;
	if (forced) {
		frappe.msgprint({
			title: "لا يمكن التعديل",
			message: "هذا الموديول مفروض من Python (Enforced by Custom App). عدّل ملف module_control/config.py ثم نفّذ مزامنة.",
			indicator: "orange",
		});
		return;
	}
	const d = MC.draft.rules[module];
	if (act === "hide") {
		d.is_enabled = 1;
		d.hide_module = d.hide_module ? 0 : 1;
		if (d.hide_module) d.hide_from_search = 1;
		// at least ensure hide-all-workspaces so card links and hidden space routes disappear
		d.hide_all_workspaces = d.hide_module ? 1 : 0;
		if (!d.hide_module) {
			d.hide_from_search = 0;
			d.block_direct_navigation = 0;
		}
	} else if (act === "block") {
		d.is_enabled = 1;
		d.block_module_access = d.block_module_access ? 0 : 1;
		d.block_direct_navigation = d.block_module_access ? 1 : 0;
		if (!d.block_module_access) d.block_protected_apis = 0;
	}
	MC.render_table();
};

MC.bulk = function (mode) {
	let mods = [];
	$wrap_or_body().find(".mc-row-check:checked").each(function () {
		mods.push(this.dataset.module);
	});
	if (!mods.length) return;
	const forced = mods.filter((x) => MC.data.modules.find((m) => m.module === x)?.py_forced);
	if (forced.length) {
		frappe.msgprint("الموديولات التالية مفروضة من Python ولن تتغير: " + forced.join(", "));
		mods = mods.filter((x) => !forced.includes(x));
	}
	mods.forEach((x) => {
		const d = MC.draft.rules[x];
		if (mode === "hide") { d.is_enabled = 1; d.hide_module = 1; d.hide_from_search = 1; d.hide_all_workspaces = 1; }
		if (mode === "unhide") { d.is_enabled = d.block_module_access ? 1 : 0; d.hide_module = 0; d.hide_from_search = 0; d.hide_all_workspaces = 0; d.block_direct_navigation = d.block_module_access ? 1 : 0; }
		if (mode === "block") { d.is_enabled = 1; d.block_module_access = 1; d.block_direct_navigation = 1; }
		if (mode === "unblock") { d.block_module_access = 0; d.block_direct_navigation = 0; d.block_protected_apis = 0; d.is_enabled = d.hide_module ? 1 : 0; }
	});
	MC.render_table();
};

MC.payload = function () {
	const rules = [];
	MC.data.modules.forEach((m) => {
		const r = m.rule || {};
		const d = MC.draft.rules[m.module];
		const need = MC.is_changed(m.module) || Object.keys(r).length;
		rules.push({
			module: m.module,
			module_name: m.module,
			is_enabled: d.is_enabled,
			hide_module: d.hide_module,
			block_module_access: d.block_module_access,
			hide_all_workspaces: d.hide_all_workspaces,
			hide_from_search: d.hide_from_search,
			block_direct_navigation: d.block_direct_navigation,
			block_protected_apis: d.block_protected_apis,
			enforced_by: d.enforced_by || "",
			description: r.description || "",
		});
	});
	const workspace_rules = [];
	MC.data.modules.forEach((m) => {
		(m.workspaces || []).forEach((w) => {
			const d = MC.draft.workspaces[w.name];
			if (!d) return;
			workspace_rules.push({
				workspace: w.name,
				module: d.module,
				hide_workspace: d.hide ? 1 : 0,
				block_direct_navigation: d.block_nav ? 1 : 0,
				is_enabled: (d.hide || d.block_nav) ? 1 : 0,
				enforced_by: d.enforced ? "Enforced by Custom App" : "",
				description: "",
			});
		});
	});
	return {
		flags: {},
		rules,
		workspace_rules,
	};
};

MC.act_preview = function (then_apply) {
	const payload = JSON.stringify(MC.payload());
	frappe.call({
		method: MC.urls.preview,
		args: { payload },
		callback: (r) => MC.preview_dialog(r.message, then_apply),
	});
};

MC.preview_dialog = function (result, then_apply) {
	const changes = result.changes || [];
	const warnings = result.warnings || [];
	let html = "";
	if (!changes.length) {
		html = "<p style='text-align:center'>لا توجد تغييرات بين الحالة الحالية والمسودة.</p>";
	} else {
		html = `<table class="mc-table"><thead><tr><th>النوع</th><th>الهدف</th><th>من</th><th>إلى</th></tr></thead><tbody>` +
			changes.map((c) => `<tr><td>${esc(c.type)}</td><td>${esc(c.target)}</td><td>${esc(c.old)}</td><td>${esc(c.new)}</td></tr>`).join("") +
			`</tbody></table>`;
	}
	if (warnings.length) {
		html += `<div style="margin-top:10px;border:1px solid #d97b66;background:#fff4f2;border-radius:8px;padding:8px">` +
			"<b style='color:#7a1f10'>⚠ تحذيرات اعتماديات:</b><ul style='margin:6px 0 0 0'>" +
			warnings.map((w) => `<li><b>${esc(w.module)}</b>: ${esc(w.message)}${(w.parents || []).length ? " — مستخدم بواسطة: " + esc(w.parents.map((p) => p.doctype).join(", ")) : ""}</li>`).join("") +
			`</ul></div>`;
	}
	const dlg = new frappe.ui.Dialog({
		title: then_apply ? "تأكيد التطبيق — التغييرات التي ستُطبَّق" : "معاينة أثر التغييرات (Preview Impact)",
		size: "large",
		primary_action_label: then_apply ? "نعم، طبّق الآن" : "إغلاق",
		primary_action: () => {
			dlg.hide();
			if (then_apply) MC.do_apply();
		},
	});
	dlg.$body.html(`<div style="max-height:55vh;overflow:auto">${html}</div>`);
	dlg.show();
};

MC.act_apply = function () {
	// Warn about things that affect all users.
	frappe.confirm(
		"سيتم إرسال المسودة للمعاينة أولاً (نفس خطوة زر «معاينة الأثر»)، ثم بعد تأكيدك تُطبَّق على <b>جميع المستخدمين</b> مع تفريغ الكاش. هل تريد المتابعة؟",
		() => MC.act_preview(true)
	);
};

MC.do_apply = function () {
	const payload = MC.payload();
	frappe.call({
		method: MC.urls.apply,
		args: { payload: JSON.stringify(payload) },
		callback: (r) => {
			frappe.show_alert({ message: "تم التطبيق بنجاح ✅ — تم تحديث الواجهة والكاش", indicator: "green" }, 5);
			// reload form and UI to show the truly applied state (source of truth)
			MC._initialized_frm = null;
			MC.reload(() => {
				frappe.show_alert({ message: "تمت مراجعة التطبيق الفعلي من قاعدة البيانات", indicator: "green" });
			});
		},
		error: (r) => {
			frappe.msgprint({
				title: "فشل التطبيق",
				message: (r && r.exc && r.exc.replace(/<br>|&quot;/g, "")) || "خطأ غير معروف",
				indicator: "red",
			});
		},
	});
};

MC.act_sync = function () {
	frappe.call({
		method: MC.urls.sync,
		callback: (r) => {
			frappe.show_alert({ message: "تمت المزامنة ✅", indicator: "green" });
			MC._initialized_frm = null;
			MC.reload();
		},
	});
};

MC.act_scan = function () {
	frappe.call({
		method: MC.urls.scan,
		callback: (r) => {
			frappe.show_alert({ message: "تم فحص " + (r.message.count || 0) + " موديول ✅", indicator: "green" });
			MC.reload();
		},
	});
};

MC.act_restore = function () {
	frappe.confirm(
		"سيتم إزالة كل قواعد الإخفاء/الحظر التي يملكها النظام_central (وتبقى القواعد المفروضة من Python كما هي)، مع إعادة الإعدادات الافتراضية. متابعة؟",
		() => {
			frappe.call({
				method: MC.urls.restore,
				callback: (r) => {
					frappe.show_alert({ message: "تم الاسترجاع ✅", indicator: "green" });
					MC._initialized_frm = null;
					MC.reload();
				},
			});
		}
	);
};

MC.act_import = function () {
	// NOTE: هذا الموقع يحتوي سكربتات تعديل أزرار عالمية (navigation_buttons_force/global_button)
	// تعترض .btn-primary — لذا الحوار مكتفي بأزراره الداخلية المستقلة.
	const dlg = new frappe.ui.Dialog({
		title: "⬇ استيراد الإعدادات (Import Config)",
		size: "large",
		secondary_action_label: "إغلاق",
	});
	dlg.$body.html(`
		<p style="font-size:12.5px;color:#5a5f66">الصق محتوى التصدير (JSON) الناتج من زر التصدير أو من
		<code>export_config</code> في موقع آخر. تُطبَّق القواعد والإعدادات بعد المعاينة والتأكيد فقط.</p>
		<textarea class="form-control mc-import-json" rows="10" style="font-family:monospace;direction:ltr"></textarea>
		<div style="margin-top:10px;display:flex;gap:8px;align-items:center">
			<button type="button" class="btn btn-sm btn-secondary mc-import-go">👁 معاينة</button>
			<span class="mc-import-status" style="font-size:12px;color:#7a7f86"></span>
		</div>
		<div class="mc-import-results" style="margin-top:10px"></div>`);
	const $body = dlg.$body;
	$body.find(".mc-import-go").on("click", () => {
		const raw = ($body.find(".mc-import-json").val() || "").trim();
		if (!raw) {
			frappe.msgprint({ title: "لم يُدخل التصدير", message: "الصقّ محتوى JSON أولاً.", indicator: "orange" });
			return;
		}
		$body.find(".mc-import-status").text("جارٍ حساب المعاينة...");
		frappe.call({
			method: MC.urls.import,
			args: { config: raw, preview: 1 },
			callback: (r) => {
				const changes = r.message && r.message.changes || [];
				const lines = changes.length
					? changes.map((c) => `<li><b>${esc(c.type)}</b> — ${esc(c.target)}: ${esc(cstr(c.old))} → ${esc(cstr(c.new))}</li>`).join("")
					: "<li>لا يوجد فرق — الحالة مطابقة تماماً.</li>";
				const w = r.message && r.message.warnings || [];
				const wlines = w.map((x) => `<li>⚠ ${esc(x.message || x)}</li>`).join("");
				$body.find(".mc-import-status").text("");
				$body.find(".mc-import-results").html(`
					<div style="border:1px solid #eee;border-radius:8px;padding:10px;background:#fafbfc">
						<div style="font-weight:bold;margin-bottom:6px">📋 معاينة الاستيراد:</div>
						<ul style="margin:0 0 8px 16px;padding:0;max-height:220px;overflow:auto">${lines}</ul>
						${wlines || ""}
						<div style="display:flex;gap:8px;margin-top:8px;flex-direction:row-reverse">
							<button type="button" class="btn btn-sm btn-primary mc-import-apply">💾 تطبيق الآن على جميع المستخدمين</button>
							<button type="button" class="btn btn-sm btn-secondary mc-import-cancel">✖ إلغاء</button>
						</div>
					</div>`);
				$body.find(".mc-import-cancel").on("click", () => $body.find(".mc-import-results").empty());
				$body.find(".mc-import-apply").on("click", () => {
					$body.find(".mc-import-apply").prop("disabled", true);
					frappe.call({
						method: MC.urls.import,
						args: { config: raw, preview: 0 },
						callback: (r2) => {
							frappe.show_alert({ message: "تم استيراد الإعدادات وتطبيقها ✅", indicator: "green" }, 5);
							$body.find(".mc-import-results").empty();
							$body.find(".mc-import-status").text("تم التطبيق ✅");
							dlg.hide();
							MC._initialized_frm = null;
							MC.reload();
						},
					});
				});
			},
		});
	});
	dlg.show();
};

MC.act_compat = function () {
	frappe.call({
		method: MC.urls.compat,
		callback: (r) => {
			const checks = (r.message && r.message.checks) || [];
			const okAll = r.message && r.message.ok;
			const rows = checks.map(
				(c) => `<tr>
					<td style="width:26px">${c.ok ? "✅" : "❌"}</td>
					<td>${esc(c.name)}</td>
					<td style="color:#7a7f86">${esc(c.detail || "")}</td></tr>`
			).join("");
			const dlg = new frappe.ui.Dialog({
				title: okAll ? "🧪 فحص التوافق — سليم" : "🧪 فحص التوافق — توجد مشاكل",
				size: "large",
			});
			dlg.$body.html(`
				<div style="margin-bottom:8px;font-size:12.5px;color:${okAll ? "#206b20" : "#7a1f10"}">
				${okAll ? "جميع نقاط التكامل مع نواة Frappe سليمة ✅" : "توجد نقاط تكامل مفقودة/متجاوزة! راجع TROUBLESHOOTING.md"}</div>
				<table class="mc-table"><thead><tr><th style="width:26px"></th><th>نقطة التكامل</th><th>التفصيل</th></tr></thead>
				<tbody>${rows}</tbody></table>`);
			dlg.show();
		},
	});
};

MC.show_audit = function () {
	if (!MC.data || !MC.data.audit) return;
	const rows = (MC.data.audit || []).map(
		(a) => `<tr>
			<td>${esc(a.timestamp)}</td><td>${esc(a.user)}</td><td>${esc(a.source)}</td>
			<td><b>${esc(a.target_type)}</b> ${esc(a.target_name)}</td>
			<td>${esc(a.old_state)} → ${esc(a.new_state)}</td>
			<td>${esc(a.status)}</td></tr>`
	);
	const dlg = new frappe.ui.Dialog({ title: "🧾 سجل التدقيق — آخر 25 عملية", size: "large" });
	dlg.$body.html(`
	<table class="mc-table"><thead><tr><th>وقت</th><th>مستخدم</th><th>مصدر</th><th>الهدف</th><th>التغيير</th><th>حالة</th></tr></thead>
	<tbody>${rows.join("") || "<tr><td colspan='6'>لا يوجد سجل بعد</td></tr>"}</tbody></table>`);
	dlg.show();
};

MC.show_impact = function (module, impact) {
	if (!impact) return;
	const parents = impact.parents || [];
	const reports = impact.reports || [];
	const dlg = new frappe.ui.Dialog({ title: "⚠ التبعيات — " + module, size: "large" });
	dlg.$body.html(
		`<div style="max-height:55vh;overflow:auto">
		${impact.warn
			? `<div style="border:1px solid #d97b66;border-radius:8px;background:#fff4f2;padding:8px;margin-bottom:8px;color:#7a1f10"><b>تحذير:</b> هذا الموديول مُستخدَم من غيره؛ تفعيل الحظر الفعلي قد يؤثر على الوظائف التالية.</div>`
			: `<div style="color:#206b20;margin-bottom:8px">لا توجد اعتماديات خطيرة مكتشفة.</div>`}
		${parents.length ? "<b>مستندات مرتبطة من موديولات أخرى (ستتأثر بالحظر):</b><ul>" + parents.map((p) => `<li>${esc(p.doctype)} — موديول ${esc(p.module)}</li>`).join("") + "</ul>" : ""}
		${reports.length ? "<b>تقارير مرتبطة من موديولات أخرى:</b><ul>" + reports.map((p) => `<li>${esc(p.report)} — موديول ${esc(p.module)}</li>`).join("") + "</ul>" : ""}
		${impact.target_doctypes ? `<div class="mc-count">DocTypes داخل الموديول: ${impact.target_doctypes.length}</div>` : ""}
		</div>`
	);
	dlg.show();
};

MC.ws_dialog = function (module) {
	const m = MC.data.modules.find((x) => x.module === module);
	if (!m) return;
	const rows = (m.workspaces || [])
		.map((w) => {
			const d = MC.draft.workspaces[w.name];
			const current_db = w.mc_hidden || w.rule_hide;
			return `<tr>
			<td>${esc(w.name)} ${w.is_hidden ? '<span class="mc-chip mc-chip-force">مخفية أصلاً من Frappe</span>' : ""} ${d.enforced ? '<span class="mc-chip mc-chip-force">Enforced</span>' : ""}</td>
			<td>${w.public ? "عامة" : "خاصة"}</td>
			<td style="text-align:center">
				<label style="font-size:12px;margin-inline-end:10px"><input type="checkbox" class="mc-ws-hide" data-ws="${esc(w.name)}" ${d.hide ? "checked" : ""} ${d.enforced ? "disabled" : ""}> إخفاء</label>
				<label style="font-size:12px"><input type="checkbox" class="mc-ws-nav" data-ws="${esc(w.name)}" ${d.block_nav ? "checked" : ""} ${d.enforced ? "disabled" : ""}> منع تنقل</label>
				${current_db !== (d.hide || d.block_nav) ? '<span class="mc-chip mc-chip-diff">تغيير</span>' : ""}
			</td></tr>`;
		})
		.join("");
	const dlg = new frappe.ui.Dialog({
		title: "🗂 مساحات الموديول — " + module,
		size: "large",
		primary_action_label: "تم",
		primary_action: () => dlg.hide(),
	});
	dlg.$body.html(
		`<table class="mc-table"><thead><tr><th>المساحة (الاسم الداخلي)</th><th>النوع</th><th>تحكم</th></tr></thead><tbody>${rows || "<tr><td colspan='3'>لا توجد مساحات</td></tr>"}</tbody></table>`
	);
	dlg.$body.find(".mc-ws-hide").on("change", function () {
		const w = this.dataset.ws;
		MC.draft.workspaces[w] = MC.draft.workspaces[w] || { hide: 0, block_nav: 0 };
		MC.draft.workspaces[w].hide = this.checked ? 1 : 0;
		const module_rule = MC.draft.rules[module];
		module_rule.is_enabled = 1;
	});
	dlg.$body.find(".mc-ws-nav").on("change", function () {
		const w = this.dataset.ws;
		MC.draft.workspaces[w] = MC.draft.workspaces[w] || { hide: 0, block_nav: 0 };
		MC.draft.workspaces[w].block_nav = this.checked ? 1 : 0;
		MC.draft.rules[module].is_enabled = 1;
	});
	dlg.show();
};
