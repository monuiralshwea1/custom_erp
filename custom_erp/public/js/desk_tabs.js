/* Custom ERP — Tabbed MDI for ERPNext Desk
 *
 * Adds a horizontal tab bar below the navbar that tracks Desk routes.
 * - One tab per opened route (forms, lists, reports, pages, workspaces).
 * - Click a tab to navigate via frappe.set_route (native routing, permissions kept).
 * - Close any tab with x (or middle-click); closing the active tab jumps to a neighbour.
 * - The first (home) tab is pinned and cannot be closed.
 * - New (unsaved) form tab is renamed to the real document route after save.
 * - Open tabs + active tab persist per user in localStorage (metadata only).
 * - No core files touched, no timers/polling, no iframes, no monkey-patching.
 */

(function () {
	"use strict";

	if (window.__custom_erp_desk_tabs_init) {
		return;
	}
	window.__custom_erp_desk_tabs_init = true;

	var DT_VERSION = "1.0.3";
	try {
		if (window.console && console.log) {
			console.log("[desk-tabs] script loaded v" + DT_VERSION);
		}
	} catch (e) {
		/* ignore */
	}

	var BAR_ID = "custom-erp-desk-tabs";
	var STORE_PREFIX = "custom_erp_desk_tabs_v1__";
	var MAX_TABS = 50;

	/* Routes that must never appear as tabs (non-Desk entry points). */
	var SKIP_HEADS = {
		login: 1,
		"setup-wizard": 1,
		"update-password": 1,
		"social-login": 1,
		forgot: 1,
		signup: 1,
	};

	var state = {
		tabs: [], // [{ key, route:[...], text, name, icon, pinned }]
		active_key: null,
		last_key: null,
	};

	function is_arabic() {
		try {
			var lang = (frappe.boot && frappe.boot.lang) || "en";
			return String(lang).toLowerCase().indexOf("ar") === 0;
		} catch (e) {
			return false;
		}
	}

	var STR = {
		ar: {
			home: "الرئيسية",
			list: "قائمة",
			tree: "شجرة",
			new_doc: "جديد",
			close: "إغلاق التبويب",
			bar_label: "التبويبات المفتوحة",
		},
		en: {
			home: "Home",
			list: "List",
			tree: "Tree",
			new_doc: "New",
			close: "Close tab",
			bar_label: "Open tabs",
		},
	};

	function t(key) {
		var pack = is_arabic() ? STR.ar : STR.en;
		return pack[key] || STR.en[key] || key;
	}

	function tr(s) {
		try {
			if (typeof __ === "function") {
				return __(s);
			}
		} catch (e) {
			/* ignore */
		}
		return s;
	}

	function store_key() {
		try {
			var user = frappe.session && frappe.session.user;
			if (!user || user === "Guest") {
				return null;
			}
			return STORE_PREFIX + user;
		} catch (e) {
			return null;
		}
	}

	function current_route() {
		try {
			var r = frappe.get_route && frappe.get_route();
			if (r && Array.isArray(r) && r.length) {
				return r.slice();
			}
		} catch (e) {
			/* ignore */
		}
		return null;
	}

	function is_new_form_route(route) {
		if (!route || route[0] !== "Form") {
			return false;
		}
		if (route.length < 3 || route[2] === undefined || route[2] === null || route[2] === "") {
			return true;
		}
		return /^new-/i.test(String(route[2]));
	}

	function icon_for(route) {
		var head = route[0];
		if (head === "Form") {
			return "📄";
		}
		if (head === "List") {
			return "📋";
		}
		if (head === "Tree") {
			return "🌳";
		}
		if (head === "query-report" || head === "Report" || head === "Dashboard") {
			return "📊";
		}
		if (head === "Page") {
			return "📑";
		}
		if (head === "Workspaces") {
			return "📌";
		}
		return "🧾";
	}

	/* Build a clear, human-readable title from the route only (no doc fetch). */
	function title_for(route) {
		var head = route[0];
		if (head === "Form") {
			var doctype = route[1] || "";
			var label = tr(doctype);
			if (is_new_form_route(route)) {
				return { text: t("new_doc") + ": " + label, name: "" };
			}
			return { text: label, name: String(route[2]) };
		}
		if (head === "List") {
			var ldt = tr(route[1] || "");
			var suffix = "";
			if (route[2] && String(route[2]).toLowerCase() !== "list") {
				suffix = " (" + tr(route[2]) + ")";
			}
			return { text: t("list") + ": " + ldt + suffix, name: "" };
		}
		if (head === "Tree") {
			return { text: t("tree") + ": " + tr(route[1] || ""), name: "" };
		}
		if (head === "query-report") {
			return { text: tr(String(route[1] || "")), name: "" };
		}
		if (head === "Page" || head === "Dashboard" || head === "Report") {
			return { text: tr(String(route[1] || head)), name: "" };
		}
		if (head === "Workspaces") {
			return { text: tr(String(route[1] || t("home"))), name: "" };
		}
		return { text: route.join(" / "), name: "" };
	}

	function find_tab(key) {
		for (var i = 0; i < state.tabs.length; i++) {
			if (state.tabs[i].key === key) {
				return state.tabs[i];
			}
		}
		return null;
	}

	function remove_tab(key) {
		for (var i = 0; i < state.tabs.length; i++) {
			if (state.tabs[i].key === key) {
				state.tabs.splice(i, 1);
				return i;
			}
		}
		return -1;
	}

	function upsert_tab(key, route) {
		var info = title_for(route);
		var existing = find_tab(key);
		if (existing) {
			existing.route = route.slice();
			existing.text = info.text;
			existing.name = info.name;
			existing.icon = icon_for(route);
			return existing;
		}
		var tab = {
			key: key,
			route: route.slice(),
			text: info.text,
			name: info.name,
			icon: icon_for(route),
			pinned: false, // all tabs are closable (no pinned home tab)
		};
		state.tabs.push(tab);
		/* cap the number of tabs: drop oldest unpinned, non-active tab */
		while (state.tabs.length > MAX_TABS) {
			var dropped = false;
			for (var i = 0; i < state.tabs.length; i++) {
				if (!state.tabs[i].pinned && state.tabs[i].key !== state.active_key) {
					state.tabs.splice(i, 1);
					dropped = true;
					break;
				}
			}
			if (!dropped) {
				break;
			}
		}
		return tab;
	}

	function persist() {
		var key = store_key();
		if (!key) {
			return;
		}
		try {
			var data = {
				tabs: state.tabs.map(function (tab) {
					return {
						key: tab.key,
						route: tab.route,
						text: tab.text,
						name: tab.name,
						icon: tab.icon,
						pinned: !!tab.pinned,
					};
				}),
				active_key: state.active_key,
			};
			window.localStorage.setItem(key, JSON.stringify(data));
		} catch (e) {
			/* storage full or unavailable: tabs simply won't persist */
		}
	}

	function valid_restored_tab(item) {
		if (!item || typeof item.key !== "string" || !Array.isArray(item.route)) {
			return false;
		}
		if (!item.route.length || typeof item.route[0] !== "string") {
			return false;
		}
		if (SKIP_HEADS[item.route[0]]) {
			return false;
		}
		return true;
	}

	function restore() {
		var key = store_key();
		if (!key) {
			return;
		}
		try {
			var raw = window.localStorage.getItem(key);
			if (!raw) {
				return;
			}
			var data = JSON.parse(raw);
			if (!data || !Array.isArray(data.tabs)) {
				return;
			}
			var tabs = [];
			for (var i = 0; i < data.tabs.length && tabs.length < MAX_TABS; i++) {
				var item = data.tabs[i];
				if (!valid_restored_tab(item)) {
					continue;
				}
				var route = item.route.slice();
				var info = title_for(route);
				tabs.push({
					key: item.key,
					route: route,
					text: info.text,
					name: info.name,
					icon: item.icon || icon_for(route),
					pinned: false, // all tabs closable, incl. restored ones
				});
			}
			if (!tabs.length) {
				return;
			}
			state.tabs = tabs;
			if (typeof data.active_key === "string" && find_tab(data.active_key)) {
				state.active_key = data.active_key;
				state.last_key = data.active_key;
			}
		} catch (e) {
			/* corrupted storage: start fresh */
			state.tabs = [];
			state.active_key = null;
			state.last_key = null;
		}
	}

	function ensure_bar() {
		var bar = document.getElementById(BAR_ID);
		if (bar) {
			return bar;
		}
		bar = document.createElement("div");
		bar.id = BAR_ID;
		bar.setAttribute("role", "navigation");
		bar.setAttribute("aria-label", t("bar_label"));

		/* same content width as the navbar: Bootstrap .container */
		var box = document.createElement("div");
		box.className = "container dt-tabs-container";
		bar.appendChild(box);

		var strip = document.createElement("div");
		strip.className = "dt-tabs-strip";
		box.appendChild(strip);

		/* middle-click closes a tab */
		bar.addEventListener("auxclick", function (e) {
			if (e && e.button === 1) {
				var el = e.target && e.target.closest ? e.target.closest(".dt-tab") : null;
				if (el && el.dataset && el.dataset.key) {
					e.preventDefault();
					close_tab(el.dataset.key);
				}
			}
		});

		/* below the navbar, above the page content */
		var body = document.getElementById("body");
		if (body && body.firstChild) {
			body.insertBefore(bar, body.firstChild);
		} else if (body) {
			body.appendChild(bar);
		} else {
			document.body.insertBefore(bar, document.body.firstChild);
		}
		return bar;
	}

	function make_tab_el(tab, is_active) {
		var btn = document.createElement("button");
		btn.type = "button";
		btn.className = "dt-tab" + (is_active ? " dt-active" : "") + (tab.pinned ? " dt-pinned" : "");
		btn.dataset.key = tab.key;
		btn.title = tab.name ? tab.text + ": " + tab.name : tab.text;

		var icon = document.createElement("span");
		icon.className = "dt-icon";
		icon.setAttribute("aria-hidden", "true");
		icon.textContent = tab.icon;
		btn.appendChild(icon);

		var label = document.createElement("span");
		label.className = "dt-label";
		label.textContent = tab.text;
		btn.appendChild(label);

		if (tab.name) {
			var nm = document.createElement("span");
			nm.className = "dt-name";
			nm.setAttribute("dir", "auto");
			nm.textContent = tab.name;
			btn.appendChild(nm);
		}

		if (!tab.pinned) {
			var x = document.createElement("span");
			x.className = "dt-close";
			x.setAttribute("role", "button");
			x.setAttribute("aria-label", t("close"));
			x.title = t("close");
			x.textContent = "×";
			x.addEventListener("click", function (e) {
				e.preventDefault();
				e.stopPropagation();
				close_tab(tab.key);
			});
			btn.appendChild(x);
		}

		btn.addEventListener("click", function () {
			if (tab.key !== state.active_key) {
				/* native routing: permissions, validation and warnings stay intact */
				frappe.set_route(tab.route.slice());
			}
		});

		return btn;
	}

	function render() {
		var bar = ensure_bar();
		var strip = bar.querySelector(".dt-tabs-strip");
		if (!strip) {
			return;
		}
		while (strip.firstChild) {
			strip.removeChild(strip.firstChild);
		}
		var active_el = null;
		for (var i = 0; i < state.tabs.length; i++) {
			var tab = state.tabs[i];
			var is_active = tab.key === state.active_key;
			var el = make_tab_el(tab, is_active);
			strip.appendChild(el);
			if (is_active) {
				active_el = el;
			}
		}
		/* keep the active tab visible when many tabs overflow */
		if (active_el && active_el.scrollIntoView) {
			try {
				active_el.scrollIntoView({ block: "nearest", inline: "nearest" });
			} catch (e) {
				/* older browsers: ignore */
			}
		}
	}

	/* Close a tab. Inactive: just remove. Active: jump to a neighbour. */
	function close_tab(key) {
		var idx = -1;
		for (var i = 0; i < state.tabs.length; i++) {
			if (state.tabs[i].key === key) {
				idx = i;
				break;
			}
		}
		if (idx === -1) {
			return;
		}
		if (state.tabs[idx].pinned) {
			return; // pinned home tab cannot be closed
		}
		var was_active = key === state.active_key;
		state.tabs.splice(idx, 1);

		var neighbour = null;
		if (was_active && state.tabs.length) {
			neighbour = state.tabs[Math.min(idx, state.tabs.length - 1)];
			state.active_key = neighbour.key;
			state.last_key = neighbour.key;
		} else if (was_active) {
			state.active_key = null;
			state.last_key = null;
		}
		persist();
		if (neighbour) {
			frappe.set_route(neighbour.route.slice());
		} else {
			render();
		}
	}

	function on_route_change() {
		var route = current_route();
		if (!route) {
			return;
		}
		if (SKIP_HEADS[route[0]]) {
			return;
		}
		var key = route.join("/");

		/* A new (unsaved) form got its real name after save:
		   rename that tab instead of leaving two tabs for one document. */
		if (state.last_key && state.last_key !== key) {
			var prev = find_tab(state.last_key);
			if (
				prev &&
				route[0] === "Form" &&
				prev.route[0] === "Form" &&
				prev.route[1] === route[1] &&
				is_new_form_route(prev.route)
			) {
				remove_tab(state.last_key);
			}
		}

		upsert_tab(key, route);
		state.active_key = key;
		state.last_key = key;
		persist();
		render();
	}

	var initialized = false;

	function init() {
		if (initialized) {
			return;
		}
		try {
			if (!window.frappe || !frappe.router || typeof frappe.router.on !== "function") {
				return;
			}
			if (!frappe.session || !frappe.session.user || frappe.session.user === "Guest") {
				return;
			}
			restore();
			/* single, event-driven subscription — no timers, no DOM polling */
			frappe.router.on("change", on_route_change);
			/* seed the current route in case the router already resolved */
			on_route_change();
			initialized = true;
			try {
				if (window.console && console.log) {
					console.log("[desk-tabs] initialized, tabs: " + state.tabs.length);
				}
			} catch (e2) {
				/* ignore */
			}
		} catch (e) {
			if (window.console && console.warn) {
				console.warn("[desk-tabs] init skipped:", e);
			}
		}
	}

	/* Try now (covers late loads), on Desk startup and on window load
	   (covers early loads before frappe.session exists). No polling. */
	init();
	try {
		var jq = window.jQuery || window.$;
		if (jq && typeof jq === "function") {
			jq(document).one("startup", init);
		}
		if (typeof window.addEventListener === "function") {
			window.addEventListener("load", init, { once: true });
		}
	} catch (e) {
		/* ignore */
	}
})();
