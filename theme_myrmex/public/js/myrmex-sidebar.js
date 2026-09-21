// Sidebar behaviour for the Frappe v15 Desk.
//
// v15 renders the workspace sidebar inside each page:
//   .layout-side-section > .list-sidebar.overlay-sidebar > .desk-sidebar
//     > .standard-sidebar-section > .sidebar-item-container > .item-anchor
// and ships its own toggle (.page-head .sidebar-toggle-btn) that hides the
// sidebar on desktop and opens it as an overlay drawer on mobile.
//
// Myrmex keeps that native toggle and drawer exactly as they are, and adds:
//   * a brand block at the top of the workspace sidebar;
//   * a collapsed "rail" mode for the workspace sidebar on desktop, toggled
//     from the navbar button or Ctrl/Cmd+B, and remembered across reloads;
//   * a floating tooltip for rail items (a CSS ::after would be clipped by the
//     sidebar's own scroll container).
// Nothing is re-parented or removed.

const myrmex = window.myrmex;

const COLLAPSED_CLASS = "myrmex-sidebar-collapsed";
const STORAGE_KEY = "sidebar-collapsed";

myrmex.sidebar = {
	init() {
		this.restoreState();
		this.mountTooltip();

		myrmex.onRoute(() => {
			const page = myrmex.currentPage();
			const deskSidebar = page && page.querySelector(".desk-sidebar");
			myrmex.ROOT.classList.toggle("myrmex-has-rail", !!deskSidebar);
			if (!deskSidebar) return;

			this.mountBrand(deskSidebar);
			this.decorateItems(deskSidebar);
			// Workspace items stream in after an XHR and are re-rendered in
			// edit mode, with no event to hook. One scoped observer, dropped on
			// the next route change.
			myrmex.observe(deskSidebar, () => this.decorateItems(deskSidebar));
		});

		document.addEventListener("keydown", (event) => {
			if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey) return;
			if (event.key.toLowerCase() !== "b") return;
			// Leave Ctrl+B to text fields and editors, where it means bold.
			if (myrmex.isTypingTarget(event.target)) return;
			if (myrmex.isMobile()) return;
			event.preventDefault();
			this.toggle();
		});

		// A tap on an item inside the native mobile drawer should close it.
		document.addEventListener("click", (event) => {
			if (!myrmex.isMobile()) return;
			if (!event.target.closest(".overlay-sidebar.opened .item-anchor")) return;
			const backdrop = document.querySelector(".layout-side-section .close-sidebar");
			if (backdrop) backdrop.click();
		});
	},

	restoreState() {
		const boot = frappe.boot && frappe.boot.myrmex_theme;
		const fallback = boot ? !!boot.collapse_sidebar_by_default : false;
		myrmex.ROOT.classList.toggle(COLLAPSED_CLASS, !!myrmex.storage.get(STORAGE_KEY, fallback));
	},

	isCollapsed() {
		return myrmex.ROOT.classList.contains(COLLAPSED_CLASS);
	},

	/**
	 * Workspace pages: switch between the full sidebar and the rail.
	 * Other pages (list, form, report): defer to Frappe's own toggle, so the
	 * shortcut does the same thing the page's sidebar button does.
	 */
	toggle() {
		const page = myrmex.currentPage();
		if (!page) return;

		if (page.querySelector(".desk-sidebar")) {
			const collapsed = !this.isCollapsed();
			myrmex.ROOT.classList.toggle(COLLAPSED_CLASS, collapsed);
			myrmex.storage.set(STORAGE_KEY, collapsed);
			this.hideTooltip();
			document.dispatchEvent(new CustomEvent("myrmex:sidebar-change", { detail: { collapsed } }));
			// Charts and datatables measure their container.
			window.dispatchEvent(new Event("resize"));
			return;
		}

		const nativeToggle = page.querySelector(".page-head .sidebar-toggle-btn");
		if (nativeToggle && nativeToggle.offsetParent !== null) nativeToggle.click();
	},

	mountBrand(deskSidebar) {
		myrmex.once(deskSidebar, "Brand", () => {
			const brandText =
				(frappe.boot && frappe.boot.sysdefaults && frappe.boot.sysdefaults.app_name) ||
				(frappe.boot && frappe.boot.app_name) ||
				"Myrmex";
			const brand = document.createElement("a");
			brand.className = "myrmex-sidebar-brand";
			brand.href = "/app";
			brand.setAttribute("aria-label", brandText);
			brand.innerHTML = `
				<span class="myrmex-mark" aria-hidden="true">${myrmex.escape(brandText.charAt(0).toUpperCase())}</span>
				<span class="myrmex-wordmark">${myrmex.escape(brandText)}</span>
			`;
			deskSidebar.prepend(brand);
		});
	},

	/** Copy each label into a data attribute for the rail tooltip. */
	decorateItems(deskSidebar) {
		deskSidebar.querySelectorAll(".sidebar-item-container").forEach((item) => {
			const label = item.querySelector(":scope > .desk-sidebar-item .sidebar-item-label");
			const text = label ? label.textContent.trim() : "";
			if (text && item.dataset.myrmexLabel !== text) item.dataset.myrmexLabel = text;
		});
	},

	// --- rail tooltip --------------------------------------------------------

	mountTooltip() {
		if (this.tooltip) return;
		const tip = document.createElement("div");
		tip.className = "myrmex-tooltip";
		tip.setAttribute("role", "tooltip");
		tip.hidden = true;
		document.body.appendChild(tip);
		this.tooltip = tip;

		const show = (event) => {
			if (!this.isCollapsed() || myrmex.isMobile()) return;
			const anchor = event.target.closest(".desk-sidebar .item-anchor");
			if (!anchor) return;
			const item = anchor.closest(".sidebar-item-container");
			const text = item && item.dataset.myrmexLabel;
			if (!text) return;

			const rect = anchor.getBoundingClientRect();
			const rtl = document.documentElement.dir === "rtl";
			tip.textContent = text;
			tip.hidden = false;
			tip.style.top = `${rect.top + rect.height / 2}px`;
			tip.style.left = rtl ? "" : `${rect.right + 10}px`;
			tip.style.right = rtl ? `${window.innerWidth - rect.left + 10}px` : "";
		};

		document.addEventListener("mouseover", show);
		document.addEventListener("focusin", show);
		document.addEventListener("mouseout", (event) => {
			if (event.target.closest(".desk-sidebar .item-anchor")) this.hideTooltip();
		});
		document.addEventListener("focusout", () => this.hideTooltip());
		window.addEventListener("scroll", () => this.hideTooltip(), { passive: true, capture: true });
	},

	hideTooltip() {
		if (this.tooltip) this.tooltip.hidden = true;
	},
};

myrmex.ready(() => myrmex.sidebar.init());

export default myrmex.sidebar;
