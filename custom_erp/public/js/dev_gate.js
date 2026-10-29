// Central Module Control — dev-pages gate (client side message polish).
// Server side is the real enforcement (module_control/permissions.py → 403).
// This file only makes the full-page "not permitted" card show the exact
// developer-only message instead of the generic desk text, and ONLY when
// the attempted page is one of the dev interfaces.
(function () {
	const DEV_ACCESS_MESSAGE =
		"ليس لك إذن الوصول لهذه الصفحة — خاصة بالمطوّر (أدوارها متاحة لحساب Administrator فقط)";

	// route fragments / rendered names of the dev pages (both languages)
	const DEV_HINTS = [
		"Module Control Settings",
		"Module Control Rule",
		"Workspace Control Rule",
		"Module Control Audit Log",
		"module-control-settings",
		"module-control-rule",
		"workspace-control-rule",
		"module-control-audit-log",
		"إعدادات التحكم في الموديولات",
		"قاعدة التحكم في مساحات العمل",
		"سجل التدقيق",
	];

	const _is_dev = (s) => DEV_HINTS.some((h) => String(s || "").includes(h));

	function show_dev_card(page_name) {
		frappe.show_message_page({
			page_name: page_name,
			icon: "octicon octicon-circle-slash",
			message: DEV_ACCESS_MESSAGE,
		});
		// clear any stale generic msgprint modal behind ours
		try {
			frappe.hide_msgprint && frappe.hide_msgprint();
		} catch (e) {
			/* noop */
		}
	}

	function patch_show_not_permitted() {
		if (!frappe || frappe._mc_dev_gate_patched) return;
		const orig = frappe.show_not_permitted;
		frappe.show_not_permitted = function (page_name) {
			if (_is_dev(page_name)) {
				show_dev_card(page_name);
			} else if (orig) {
				return orig(page_name);
			}
		};
		frappe._mc_dev_gate_patched = true;
	}

	if (window.__frappeClient) {
		patch_show_not_permitted();
	} else {
		// app_include_js runs after the desk bundle; be defensive anyway
		setTimeout(patch_show_not_permitted, 0);
	}
})();
