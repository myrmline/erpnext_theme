// Shared plumbing: the namespace, route hooks, and a disciplined observer.
//
// Frappe rebuilds large parts of the DOM on every route change, so the theme
// needs to re-attach. It does that by listening to Frappe's own events. Timed
// guesses (setTimeout polling) are not used anywhere in this app.

const myrmex = (window.myrmex = window.myrmex || {});

myrmex.version = "1.1.0";
myrmex.ROOT = document.documentElement;

// --- one-time guards -------------------------------------------------------

/**
 * Run `fn` against `element` only once, ever. The marker lives on the element,
 * so a re-rendered node is treated as new and a surviving node is skipped.
 */
myrmex.once = function (element, key, fn) {
	if (!element) return false;
	const flag = `myrmex${key}`;
	if (element.dataset[flag]) return false;
	element.dataset[flag] = "1";
	fn(element);
	return true;
};

// --- route handling --------------------------------------------------------

const routeHandlers = [];

/**
 * Register a callback for "the page just changed". Fires on the initial load
 * and on every subsequent Desk navigation.
 */
myrmex.onRoute = function (fn) {
	routeHandlers.push(fn);
	if (myrmex._booted) safely(fn);
};

function safely(fn) {
	try {
		fn(frappe.get_route ? frappe.get_route() : []);
	} catch (error) {
		console.error("[myrmex] handler failed", error);
	}
}

function runRouteHandlers() {
	routeHandlers.forEach(safely);
}

myrmex.bindRouting = function () {
	if (myrmex._routingBound) return;
	myrmex._routingBound = true;

	// frappe.router is the canonical signal in v15.
	if (frappe.router && frappe.router.on) {
		frappe.router.on("change", () => {
			disconnectScoped();
			runRouteHandlers();
		});
	}

	// page-change covers the cases the router does not emit for (first paint of
	// a page object, workspace switches inside the same route).
	$(document).on("page-change", () => {
		disconnectScoped();
		runRouteHandlers();
	});

	$(document).on("form-refresh list-view-refresh", () => runRouteHandlers());
};

// --- scoped mutation observers --------------------------------------------

const scopedObservers = [];

/**
 * Observe one container, not the document.
 *
 * The callback is throttled to one animation frame, the observer is registered
 * so it can be disconnected on the next route change, and re-observing the same
 * node is a no-op. Use this only where Frappe gives no event to hook.
 */
myrmex.observe = function (target, callback, options) {
	if (!target || target.dataset.myrmexObserved) return null;
	target.dataset.myrmexObserved = "1";

	let frame = null;
	const observer = new MutationObserver(() => {
		if (frame) return;
		frame = requestAnimationFrame(() => {
			frame = null;
			try {
				callback(target);
			} catch (error) {
				console.error("[myrmex] observer callback failed", error);
			}
		});
	});

	observer.observe(target, Object.assign({ childList: true, subtree: true }, options || {}));
	scopedObservers.push({ observer, target });
	callback(target);
	return observer;
};

function disconnectScoped() {
	while (scopedObservers.length) {
		const entry = scopedObservers.pop();
		entry.observer.disconnect();
		if (entry.target) delete entry.target.dataset.myrmexObserved;
	}
}

myrmex.disconnectObservers = disconnectScoped;

// Leaving the tab or the app should not leave observers running.
window.addEventListener("beforeunload", disconnectScoped);

// --- small helpers ---------------------------------------------------------

myrmex.storage = {
	get(key, fallback) {
		try {
			const value = window.localStorage.getItem(`myrmex:${key}`);
			return value === null ? fallback : JSON.parse(value);
		} catch (error) {
			return fallback;
		}
	},
	set(key, value) {
		try {
			window.localStorage.setItem(`myrmex:${key}`, JSON.stringify(value));
		} catch (error) {
			// Private browsing or a full quota: state simply does not persist.
		}
	},
};

/** Same API as myrmex.storage, but cleared when the tab closes. */
myrmex.sessionStore = {
	get(key, fallback) {
		try {
			const value = window.sessionStorage.getItem(`myrmex:${key}`);
			return value === null ? fallback : JSON.parse(value);
		} catch (error) {
			return fallback;
		}
	},
	set(key, value) {
		try {
			window.sessionStorage.setItem(`myrmex:${key}`, JSON.stringify(value));
		} catch (error) {
			// Storage unavailable: the value lives for this page view only.
		}
	},
	remove(key) {
		try {
			window.sessionStorage.removeItem(`myrmex:${key}`);
		} catch (error) {
			// Nothing to clean up.
		}
	},
};

myrmex.isMobile = () => window.matchMedia("(max-width: 991px)").matches;

/** The wrapper element of the page Frappe is currently showing. */
myrmex.currentPage = function () {
	const page = window.frappe && frappe.container && frappe.container.page;
	if (page && page.nodeType === 1) return page;
	return document.querySelector("#body .page-container:not([style*='display: none'])");
};

/**
 * True when a keystroke belongs to a text field or rich-text editor, so global
 * shortcuts (Ctrl+B) do not steal it from bold formatting and the like.
 */
myrmex.isTypingTarget = function (target) {
	if (!target || target.nodeType !== 1) return false;
	if (target.isContentEditable) return true;
	return !!target.closest("input, textarea, select, [contenteditable=''], [contenteditable='true'], .ql-editor, .ace_editor");
};

myrmex.escape = function (value) {
	return String(value === undefined || value === null ? "" : value)
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;");
};

myrmex.ready = function (fn) {
	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", fn, { once: true });
	} else {
		fn();
	}
};

export default myrmex;
