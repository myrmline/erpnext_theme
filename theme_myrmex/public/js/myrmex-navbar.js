// Navbar behaviour: the rail toggle, elevation on scroll, and a search
// placeholder that names the shortcut.
//
// Frappe v15 markup: .sticky-top > header.navbar > .container >
//   a.navbar-brand, ul#navbar-breadcrumbs, .navbar-collapse (search + controls).
// Every native control is restyled in CSS only; this file adds one button.

const myrmex = window.myrmex;

myrmex.navbar = {
	init() {
		myrmex.onRoute(() => {
			const navbar = document.querySelector("header.navbar");
			if (!navbar) return;
			this.mountToggle(navbar);
			this.labelSearch(navbar);
			this.syncToggle();
		});

		this.trackScroll();
	},

	/**
	 * The toggle switches the workspace sidebar between full and rail. It is
	 * only shown on desktop pages that have a workspace sidebar (CSS keys off
	 * .myrmex-has-rail); list and form pages keep Frappe's own sidebar button.
	 */
	mountToggle(navbar) {
		const host = navbar.querySelector(".container") || navbar;
		myrmex.once(host, "Toggle", () => {
			const button = document.createElement("button");
			button.type = "button";
			button.className = "myrmex-nav-toggle";
			button.setAttribute("aria-label", __("Collapse sidebar"));
			button.setAttribute("title", `${__("Collapse sidebar")} (${frappe.utils.is_mac() ? "⌘" : "Ctrl+"}B)`);
			button.innerHTML = `
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
					stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<rect x="3" y="4" width="18" height="16" rx="3"></rect>
					<line x1="9" y1="4" x2="9" y2="20"></line>
				</svg>
			`;
			button.addEventListener("click", () => myrmex.sidebar.toggle());
			host.prepend(button);
			this.toggleButton = button;
		});
	},

	syncToggle() {
		const button = this.toggleButton;
		if (!button) return;
		const collapsed = myrmex.sidebar.isCollapsed();
		const label = collapsed ? __("Expand sidebar") : __("Collapse sidebar");
		button.setAttribute("aria-pressed", String(collapsed));
		button.setAttribute("aria-label", label);
		button.setAttribute("title", `${label} (${frappe.utils.is_mac() ? "⌘" : "Ctrl+"}B)`);
	},

	labelSearch(navbar) {
		const input = navbar.querySelector("#navbar-search");
		if (!input) return;
		myrmex.once(input, "SearchLabel", () => {
			const shortcut = frappe.utils.is_mac() ? "⌘G" : "Ctrl+G";
			input.setAttribute("placeholder", `${__("Search or type a command")}  ${shortcut}`);
		});
	},

	/** Lift the navbar and page header once content scrolls beneath them. */
	trackScroll() {
		if (this._scrollBound) return;
		this._scrollBound = true;

		let frame = null;
		const update = () => {
			frame = null;
			const scrolled = window.scrollY > 4;
			const navbar = document.querySelector("header.navbar");
			const page = myrmex.currentPage();
			const head = page && page.querySelector(".page-head");
			if (navbar) navbar.classList.toggle("myrmex-scrolled", scrolled);
			if (head) head.classList.toggle("myrmex-stuck", scrolled);
		};

		window.addEventListener(
			"scroll",
			() => {
				if (!frame) frame = requestAnimationFrame(update);
			},
			{ passive: true }
		);
		document.addEventListener("myrmex:sidebar-change", () => this.syncToggle());
	},
};

myrmex.ready(() => myrmex.navbar.init());

export default myrmex.navbar;
