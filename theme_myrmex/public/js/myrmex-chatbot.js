// Myrmex Assistant — the floating chat panel.
//
// Security model, as far as the browser is concerned:
//   * Config comes from frappe.boot.myrmex_chatbot (or get_config), already
//     filtered for this user. It holds no provider, model, key or prompt.
//   * The panel only tells the server *where* the user is (route + title).
//     The server reads any record data itself, with the user's permissions.
//   * Every reply is rendered from escaped text; see renderMarkdown().

const myrmex = window.myrmex;

const API = "theme_myrmex.chatbot.api.";

const ICONS = {
	send: '<path d="M4 12h13"/><path d="m12 5 7 7-7 7"/>',
	close: '<path d="M6 6l12 12"/><path d="M18 6 6 18"/>',
	minimize: '<path d="M5 12h14"/>',
	plus: '<path d="M12 5v14"/><path d="M5 12h14"/>',
	history: '<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v4h4"/><path d="M12 8v4l3 2"/>',
	back: '<path d="M15 6l-6 6 6 6"/>',
	trash: '<path d="M4 7h16"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12"/><path d="M9 7V4h6v3"/>',
	page: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6"/><path d="M9 12h6"/><path d="M9 16h3"/>',
	retry: '<path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 4v5h-5"/>',
	chevron: '<path d="m6 9 6 6 6-6"/>',
};

function icon(name) {
	return `<svg class="myrmex-chat__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
		stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]}</svg>`;
}

// ---------------------------------------------------------------------------
// Safe Markdown subset
// ---------------------------------------------------------------------------

const SAFE_URL = /^(https?:\/\/[^\s]+|\/app(\/[^\s]*)?|\/[a-z0-9][^\s]*)$/i;

function renderInline(escaped) {
	// Input is already HTML-escaped; every pattern below only wraps it in tags.
	return escaped
		.replace(/`([^`\n]+)`/g, "<code>$1</code>")
		.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
		.replace(/(^|[^*\w])\*([^*\n]+)\*(?!\w)/g, "$1<em>$2</em>")
		.replace(/\[([^\]\n]+)\]\(([^)\s]+)\)/g, (match, label, url) => {
			const raw = url.replace(/&amp;/g, "&");
			if (!SAFE_URL.test(raw) || /^\s*javascript:/i.test(raw)) return label;
			const external = /^https?:/i.test(raw);
			return `<a href="${url}"${external ? ' target="_blank" rel="noopener noreferrer"' : ""}>${label}</a>`;
		});
}

function renderMarkdown(text) {
	const source = String(text || "").replace(/\r\n?/g, "\n");
	const parts = source.split(/```[^\n]*\n?/);
	let html = "";

	parts.forEach((part, index) => {
		if (index % 2 === 1) {
			html += `<pre><code>${myrmex.escape(part.replace(/\n$/, ""))}</code></pre>`;
			return;
		}

		let list = null;
		let paragraph = [];
		const flushParagraph = () => {
			if (paragraph.length) html += `<p>${paragraph.join("<br>")}</p>`;
			paragraph = [];
		};
		const flushList = () => {
			if (list) html += `<${list.tag}>${list.items.map((item) => `<li>${item}</li>`).join("")}</${list.tag}>`;
			list = null;
		};

		part.split("\n").forEach((line) => {
			const escaped = myrmex.escape(line);
			const bullet = line.match(/^\s*[-*•]\s+(.*)$/);
			const ordered = line.match(/^\s*\d+[.)]\s+(.*)$/);
			const heading = line.match(/^\s*#{1,6}\s+(.*)$/);

			if (bullet || ordered) {
				flushParagraph();
				const tag = bullet ? "ul" : "ol";
				if (!list || list.tag !== tag) {
					flushList();
					list = { tag, items: [] };
				}
				list.items.push(renderInline(myrmex.escape((bullet || ordered)[1])));
			} else if (heading) {
				flushParagraph();
				flushList();
				html += `<p class="myrmex-chat__heading">${renderInline(myrmex.escape(heading[1]))}</p>`;
			} else if (!line.trim()) {
				flushParagraph();
				flushList();
			} else {
				flushList();
				paragraph.push(renderInline(escaped));
			}
		});
		flushParagraph();
		flushList();
	});

	return html;
}

// ---------------------------------------------------------------------------
// Route helpers
// ---------------------------------------------------------------------------

function globToRegExp(pattern) {
	const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*").replace(/\?/g, ".");
	return new RegExp(`^${escaped}$`, "i");
}

function currentRoute() {
	try {
		return (frappe.get_route() || []).filter((part) => typeof part === "string" && part);
	} catch (error) {
		return [];
	}
}

function describeRoute(route) {
	const [view, doctype, name] = route;
	if (view === "Form" && doctype && name && !String(name).startsWith("new-")) {
		return { kind: "Document", label: `${__(doctype)} ${name}` };
	}
	if (view === "Form" && doctype) return { kind: "Page", label: __("New {0}", [__(doctype)]) };
	if ((view === "List" || view === "Report") && doctype) {
		return { kind: "List", label: __("{0} list", [__(doctype)]) };
	}
	if (view === "Workspaces" && route.length > 1) {
		return { kind: "Page", label: __(route[route.length - 1]) };
	}
	const title = (document.title || "").split("|")[0].trim();
	return { kind: "Page", label: title || __("This page") };
}

// ---------------------------------------------------------------------------
// The assistant
// ---------------------------------------------------------------------------

myrmex.chatbot = {
	config: null,
	root: null,
	state: {
		open: false,
		view: "chat",
		busy: false,
		loaded: false,
		conversation: null,
		messages: [],
		includePage: true,
		unread: false,
		lastUserText: "",
	},

	init() {
		this.apply((frappe.boot && frappe.boot.myrmex_chatbot) || { enabled: false });

		if (frappe.realtime && frappe.realtime.on) {
			frappe.realtime.on("myrmex_chatbot_updated", () => this.refreshConfig());
		}

		myrmex.onRoute(() => {
			this.updateVisibility();
			this.updateContextChip();
			this.renderSuggestions();
		});
	},

	userKey(key) {
		return `chat:${frappe.session.user}:${key}`;
	},

	refreshConfig() {
		frappe.call({
			method: `${API}get_config`,
			type: "GET",
			callback: (r) => this.apply(r.message || { enabled: false }),
		});
	},

	apply(config) {
		this.config = config;
		if (!config || !config.enabled || frappe.session.user === "Guest") {
			this.unmount();
			return;
		}

		if (!this.root) this.mount();
		this.applyAppearance();
		this.renderHeader();
		this.updateVisibility();
		this.updateContextChip();

		if (!this.state.loaded) this.restore();
		this.autoOpen();
	},

	// --- mounting --------------------------------------------------------------

	mount() {
		const root = document.createElement("div");
		root.className = "myrmex-chat";
		root.innerHTML = `
			<button type="button" class="myrmex-chat__launcher" aria-expanded="false"
				aria-controls="myrmex-chat-panel">
				<span class="myrmex-chat__avatar" data-slot="launcher-avatar"></span>
				<span class="myrmex-chat__launcher-close">${icon("chevron")}</span>
				<span class="myrmex-chat__unread" hidden></span>
			</button>
			<section class="myrmex-chat__panel" id="myrmex-chat-panel" role="dialog"
				aria-modal="false" aria-labelledby="myrmex-chat-title" tabindex="-1" hidden>
				<header class="myrmex-chat__header">
					<span class="myrmex-chat__avatar" data-slot="header-avatar"></span>
					<div class="myrmex-chat__heading-text">
						<h2 class="myrmex-chat__title" id="myrmex-chat-title"></h2>
						<p class="myrmex-chat__status" aria-live="polite"></p>
					</div>
					<div class="myrmex-chat__actions">
						<button type="button" class="myrmex-chat__icon-btn" data-action="history"></button>
						<button type="button" class="myrmex-chat__icon-btn" data-action="new"></button>
						<button type="button" class="myrmex-chat__icon-btn" data-action="minimize"></button>
						<button type="button" class="myrmex-chat__icon-btn" data-action="close"></button>
					</div>
				</header>
				<div class="myrmex-chat__body">
					<div class="myrmex-chat__messages" role="log" aria-live="polite" aria-relevant="additions"></div>
					<div class="myrmex-chat__history" hidden></div>
				</div>
				<footer class="myrmex-chat__composer">
					<div class="myrmex-chat__suggestions" role="group"></div>
					<div class="myrmex-chat__context" hidden>
						${icon("page")}
						<span class="myrmex-chat__context-label"></span>
						<button type="button" class="myrmex-chat__context-toggle" aria-pressed="true"></button>
					</div>
					<form class="myrmex-chat__form" novalidate>
						<label class="sr-only" for="myrmex-chat-input"></label>
						<textarea id="myrmex-chat-input" class="myrmex-chat__input" rows="1" dir="auto"></textarea>
						<button type="submit" class="myrmex-chat__send">${icon("send")}</button>
					</form>
					<p class="myrmex-chat__hint"><span class="myrmex-chat__hint-text"></span><span class="myrmex-chat__count" hidden></span></p>
				</footer>
			</section>
		`;
		document.body.appendChild(root);
		this.root = root;

		this.$ = {
			launcher: root.querySelector(".myrmex-chat__launcher"),
			unread: root.querySelector(".myrmex-chat__unread"),
			panel: root.querySelector(".myrmex-chat__panel"),
			title: root.querySelector(".myrmex-chat__title"),
			status: root.querySelector(".myrmex-chat__status"),
			messages: root.querySelector(".myrmex-chat__messages"),
			history: root.querySelector(".myrmex-chat__history"),
			suggestions: root.querySelector(".myrmex-chat__suggestions"),
			context: root.querySelector(".myrmex-chat__context"),
			contextLabel: root.querySelector(".myrmex-chat__context-label"),
			contextToggle: root.querySelector(".myrmex-chat__context-toggle"),
			form: root.querySelector(".myrmex-chat__form"),
			input: root.querySelector(".myrmex-chat__input"),
			send: root.querySelector(".myrmex-chat__send"),
			hint: root.querySelector(".myrmex-chat__hint-text"),
			count: root.querySelector(".myrmex-chat__count"),
		};

		this.labelControls();
		this.bindEvents();
		this.mountMenuItem();
	},

	unmount() {
		if (this.root) this.root.remove();
		this.root = null;
		this.$ = null;
		this.state.open = false;
		myrmex.ROOT.classList.remove("myrmex-chat-open");
		const item = document.querySelector(".myrmex-chat-menu-item");
		if (item) item.remove();
	},

	labelControls() {
		const buttons = {
			history: [__("Conversation history"), "history"],
			new: [__("New conversation"), "plus"],
			minimize: [__("Minimize"), "minimize"],
			close: [__("Close assistant"), "close"],
		};
		for (const [action, [label, iconName]] of Object.entries(buttons)) {
			const button = this.root.querySelector(`[data-action="${action}"]`);
			button.innerHTML = icon(iconName);
			button.setAttribute("aria-label", label);
			button.setAttribute("title", label);
		}
		this.$.send.setAttribute("aria-label", __("Send message"));
		this.$.send.setAttribute("title", __("Send message"));
		this.$.input.setAttribute("placeholder", __("Ask a question…"));
		this.root.querySelector("label[for='myrmex-chat-input']").textContent = __("Message");
		this.$.hint.textContent = __("Enter to send, Shift+Enter for a new line");
	},

	bindEvents() {
		this.$.launcher.addEventListener("click", () => (this.state.open ? this.minimize() : this.open()));

		this.root.querySelector("[data-action='minimize']").addEventListener("click", () => this.minimize());
		this.root.querySelector("[data-action='close']").addEventListener("click", () => this.dismiss());
		this.root.querySelector("[data-action='new']").addEventListener("click", () => this.newConversation());
		this.root.querySelector("[data-action='history']").addEventListener("click", () =>
			this.state.view === "history" ? this.showChat() : this.showHistory()
		);

		this.$.form.addEventListener("submit", (event) => {
			event.preventDefault();
			this.submit();
		});

		this.$.input.addEventListener("keydown", (event) => {
			if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
				event.preventDefault();
				this.submit();
			}
		});
		this.$.input.addEventListener("input", () => {
			this.autosize();
			this.updateCounter();
		});

		this.$.panel.addEventListener("keydown", (event) => {
			if (event.key === "Escape") {
				event.stopPropagation();
				this.minimize();
			}
		});

		this.$.contextToggle.addEventListener("click", () => {
			this.state.includePage = !this.state.includePage;
			this.updateContextChip();
		});

		this.$.messages.addEventListener("click", (event) => {
			const retry = event.target.closest("[data-action='retry']");
			if (retry && !this.state.busy && this.state.lastUserText) {
				retry.closest(".myrmex-chat__message").remove();
				this.request(this.state.lastUserText);
			}
			// Desk links close the panel on mobile so the page is visible.
			if (event.target.closest("a[href^='/app']") && myrmex.isMobile()) this.minimize();
		});

		this.$.suggestions.addEventListener("click", (event) => {
			const chip = event.target.closest("[data-prompt]");
			if (chip && !this.state.busy) this.send(chip.dataset.prompt);
		});

		this.$.history.addEventListener("click", (event) => this.onHistoryClick(event));
	},

	/** "Show assistant" in the user menu brings the launcher back after Close. */
	mountMenuItem() {
		const menu = document.getElementById("toolbar-user");
		if (!menu || menu.querySelector(".myrmex-chat-menu-item")) return;
		const item = document.createElement("button");
		item.type = "button";
		item.className = "btn-reset dropdown-item myrmex-chat-menu-item";
		item.textContent = __("Open assistant");
		item.addEventListener("click", () => {
			myrmex.sessionStore.remove(this.userKey("dismissed"));
			this.updateVisibility();
			this.open();
		});
		menu.prepend(item);
	},

	// --- appearance ------------------------------------------------------------

	applyAppearance() {
		const look = this.config.appearance || {};
		const style = this.root.style;
		const hex = /^#[0-9a-f]{6}$/i;
		const setColor = (name, value) =>
			hex.test(value || "") ? style.setProperty(name, value) : style.removeProperty(name);

		// *-custom values feed the defaults declared on .myrmex-chat, so dark
		// mode can ignore light surface overrides while keeping the accent.
		setColor("--myrmex-chat-accent-custom", look.primary);
		setColor("--myrmex-chat-background-custom", look.background);
		setColor("--myrmex-chat-user-bubble-custom", look.user_bubble);
		setColor("--myrmex-chat-assistant-bubble-custom", look.assistant_bubble);
		const setText = (name, color) =>
			hex.test(color || "") ? style.setProperty(name, readableOn(color)) : style.removeProperty(name);
		setText("--myrmex-chat-accent-text-custom", look.primary);
		setText("--myrmex-chat-user-text-custom", look.user_bubble || look.primary);
		style.setProperty("--myrmex-chat-radius", `${clamp(look.radius, 0, 32, 16)}px`);
		style.setProperty("--myrmex-chat-width", `${clamp(look.width, 320, 720, 400)}px`);
		style.setProperty("--myrmex-chat-height", `${clamp(look.height, 420, 960, 620)}px`);

		this.root.dataset.position = this.config.position === "left" ? "left" : "right";
		const lang = this.config.language || "en";
		this.$.panel.setAttribute("lang", lang);
		if (this.config.rtl) this.$.panel.setAttribute("dir", "rtl");
		else this.$.panel.removeAttribute("dir");
	},

	renderHeader() {
		const name = this.config.name || __("Myrmex Assistant");
		this.$.title.textContent = name;
		this.syncLauncherLabel();
		this.root.querySelectorAll(".myrmex-chat__avatar").forEach((slot) => {
			slot.innerHTML = "";
			if (this.config.avatar && /^(\/|https:\/\/)/.test(this.config.avatar)) {
				const img = document.createElement("img");
				img.src = this.config.avatar;
				img.alt = "";
				slot.appendChild(img);
			} else {
				slot.textContent = name.trim().charAt(0).toUpperCase() || "M";
			}
		});
		this.setStatus();
	},

	syncLauncherLabel() {
		if (!this.$) return;
		const name = this.config.name || __("Myrmex Assistant");
		const label = this.state.open ? __("Minimize") : __("Open {0}", [name]);
		this.$.launcher.setAttribute("aria-label", label);
		this.$.launcher.setAttribute("title", label);
	},

	setStatus(text) {
		this.$.status.textContent = text || __("Uses only data you can access");
	},

	// --- visibility ------------------------------------------------------------

	isAllowedHere() {
		const behavior = this.config.behavior || {};
		const patterns = (behavior.page_patterns || []).map(globToRegExp);
		const route = currentRoute().join("/");
		const matches = patterns.some((re) => re.test(route));
		if (behavior.page_visibility === "Only on listed pages") return matches;
		if (behavior.page_visibility === "Everywhere except listed pages") return !matches;
		return true;
	},

	updateVisibility() {
		if (!this.root) return;
		const dismissed = myrmex.sessionStore.get(this.userKey("dismissed"), false);
		const allowed = this.isAllowedHere();
		this.root.hidden = !allowed || dismissed;
		if (this.root.hidden && this.state.open) this.minimize({ silent: true });
	},

	autoOpen() {
		const behavior = this.config.behavior || {};
		if (this.root.hidden || this.state.open) return;

		const minimizedThisSession = myrmex.sessionStore.get(this.userKey("minimized"), false);
		const cameFromLogin = /\/login(\?|#|$)/.test(document.referrer || "");
		const loginKey = this.userKey("login-opened");

		if (behavior.open_after_login && cameFromLogin && !myrmex.sessionStore.get(loginKey, false)) {
			myrmex.sessionStore.set(loginKey, true);
			this.open({ focus: false });
		} else if (behavior.auto_open && !minimizedThisSession) {
			this.open({ focus: false });
		}
	},

	// --- open / minimize / close -----------------------------------------------

	open({ focus = true } = {}) {
		if (!this.root || this.root.hidden) return;
		this.state.open = true;
		this.state.unread = false;
		this.$.unread.hidden = true;
		this.$.panel.hidden = false;
		// Next frame, so the CSS transition runs from the hidden state.
		requestAnimationFrame(() => this.root.classList.add("is-open"));
		this.$.launcher.setAttribute("aria-expanded", "true");
		this.syncLauncherLabel();
		myrmex.ROOT.classList.add("myrmex-chat-open");
		myrmex.sessionStore.remove(this.userKey("minimized"));

		this.ensureLoaded();
		this.updateContextChip();
		this.renderSuggestions();
		this.scrollToEnd();
		// On phones, focusing the textarea would open the keyboard over the
		// welcome and suggestions; move focus to the dialog instead.
		if (focus && !myrmex.isMobile()) this.$.input.focus();
		else if (focus) this.$.panel.focus({ preventScroll: true });
	},

	minimize({ silent = false } = {}) {
		if (!this.root) return;
		const wasOpen = this.state.open;
		this.state.open = false;
		this.root.classList.remove("is-open");
		this.$.launcher.setAttribute("aria-expanded", "false");
		this.syncLauncherLabel();
		myrmex.ROOT.classList.remove("myrmex-chat-open");
		const panel = this.$.panel;
		const hide = () => {
			if (!this.state.open) panel.hidden = true;
		};
		if (matchMedia("(prefers-reduced-motion: reduce)").matches) hide();
		else setTimeout(hide, 180);

		if (!silent) {
			myrmex.sessionStore.set(this.userKey("minimized"), true);
			if (wasOpen && !this.root.hidden) this.$.launcher.focus();
		}
	},

	/** Close hides the launcher for this browser session. */
	dismiss() {
		this.minimize({ silent: true });
		myrmex.sessionStore.set(this.userKey("dismissed"), true);
		this.updateVisibility();
		frappe.show_alert({
			message: __("Assistant hidden for this session. Open it again from your user menu."),
			indicator: "blue",
		});
	},

	// --- conversation state ----------------------------------------------------

	usesServerHistory() {
		return !!(this.config.behavior && this.config.behavior.history);
	},

	restore() {
		this.state.loaded = false;
		if (this.usesServerHistory()) {
			this.state.conversation = myrmex.storage.get(this.userKey("conversation"), null);
			this.state.messages = [];
		} else {
			this.state.conversation = null;
			this.state.messages = myrmex.sessionStore.get(this.userKey("messages"), []);
			this.state.loaded = true;
		}
		this.renderMessages();
	},

	persist() {
		if (this.usesServerHistory()) {
			myrmex.storage.set(this.userKey("conversation"), this.state.conversation);
		} else {
			const keep = this.state.messages.filter((m) => !m.error).slice(-50);
			myrmex.sessionStore.set(this.userKey("messages"), keep);
		}
	},

	ensureLoaded() {
		if (this.state.loaded) return;
		this.state.loaded = true;
		if (!this.state.conversation) {
			this.renderMessages();
			return;
		}
		this.loadConversation(this.state.conversation);
	},

	loadConversation(name) {
		this.showChat();
		this.$.messages.innerHTML = this.skeleton(3);
		frappe.call({
			method: `${API}get_conversation`,
			type: "GET",
			args: { name },
			callback: (r) => {
				const result = r.message || {};
				if (!result.ok) {
					this.state.conversation = null;
					this.state.messages = [];
				} else {
					this.state.conversation = result.conversation.name;
					this.state.messages = (result.messages || []).map((m) => ({
						role: m.role,
						content: m.content,
						error: !!m.is_error,
					}));
				}
				this.persist();
				this.renderMessages();
			},
			error: () => {
				this.$.messages.innerHTML = "";
				this.appendNotice(__("Could not load this conversation. Check your connection and try again."));
			},
		});
	},

	newConversation() {
		if (this.state.busy) return;
		this.state.conversation = null;
		this.state.messages = [];
		this.persist();
		this.showChat();
		this.renderMessages();
		this.$.input.focus();
	},

	// --- rendering -------------------------------------------------------------

	welcomeText() {
		if (this.config.welcome_message) return __(this.config.welcome_message);
		const first = (frappe.session.user_fullname || "").trim().split(/\s+/)[0];
		return first
			? __("Hello {0}! How can I help you today?", [first])
			: __("Hello! How can I help you today?");
	},

	renderMessages() {
		if (!this.$) return;
		this.$.messages.innerHTML = "";
		this.appendBubble({ role: "assistant", content: this.welcomeText(), welcome: true });
		this.state.messages.forEach((message) => this.appendBubble(message));
		this.renderSuggestions();
		this.scrollToEnd();
	},

	appendBubble(message) {
		const item = document.createElement("div");
		const role = message.role === "user" ? "user" : "assistant";
		item.className = `myrmex-chat__message is-${role}${message.error ? " is-error" : ""}${
			message.welcome ? " is-welcome" : ""
		}`;

		const bubble = document.createElement("div");
		bubble.className = "myrmex-chat__bubble";
		bubble.setAttribute("dir", "auto");
		if (role === "user" || message.error) {
			bubble.textContent = message.content;
		} else {
			bubble.innerHTML = renderMarkdown(message.content);
		}

		const sr = document.createElement("span");
		sr.className = "sr-only";
		sr.textContent = role === "user" ? __("You said:") : __("Assistant said:");
		item.appendChild(sr);
		item.appendChild(bubble);

		if (message.error && message.retry) {
			const retry = document.createElement("button");
			retry.type = "button";
			retry.className = "myrmex-chat__retry";
			retry.dataset.action = "retry";
			retry.innerHTML = `${icon("retry")}<span>${myrmex.escape(__("Try again"))}</span>`;
			item.appendChild(retry);
		}

		this.$.messages.appendChild(item);
		return item;
	},

	appendNotice(text) {
		return this.appendBubble({ role: "assistant", content: text, error: true });
	},

	renderSuggestions() {
		if (!this.$) return;
		const box = this.$.suggestions;
		const hasTurns = this.state.messages.some((m) => m.role === "user");
		const kind = describeRoute(currentRoute()).kind;
		const items = (this.config.suggestions || []).filter((s) => !s.needs || s.needs === kind);

		box.hidden = hasTurns || this.state.busy || this.state.view !== "chat" || !items.length;
		box.innerHTML = box.hidden
			? ""
			: items
					.slice(0, 6)
					.map(
						(s) =>
							`<button type="button" class="myrmex-chat__chip" data-prompt="${myrmex.escape(
								s.prompt
							)}">${myrmex.escape(s.label)}</button>`
					)
					.join("");
		box.setAttribute("aria-label", __("Suggested questions"));
	},

	updateContextChip() {
		if (!this.$) return;
		const shares = this.config.behavior && this.config.behavior.shares_page_context;
		this.$.context.hidden = !shares;
		if (!shares) return;

		const { label } = describeRoute(currentRoute());
		const on = this.state.includePage;
		this.$.context.classList.toggle("is-off", !on);
		this.$.contextLabel.textContent = on ? __("Using: {0}", [label]) : __("Page not shared");
		this.$.contextToggle.textContent = on ? __("Don't share") : __("Share page");
		this.$.contextToggle.setAttribute("aria-pressed", String(on));
		this.$.contextToggle.setAttribute(
			"aria-label",
			on ? __("Stop sharing this page with the assistant") : __("Share this page with the assistant")
		);
	},

	setBusy(busy) {
		this.state.busy = busy;
		this.$.send.disabled = busy;
		this.root.classList.toggle("is-busy", busy);
		this.setStatus(busy ? __("Thinking…") : "");

		const existing = this.$.messages.querySelector(".myrmex-chat__typing");
		if (existing) existing.remove();
		if (busy && this.config.behavior.typing_indicator) {
			const typing = document.createElement("div");
			typing.className = "myrmex-chat__message is-assistant myrmex-chat__typing";
			typing.innerHTML = `<div class="myrmex-chat__bubble"><span class="sr-only">${myrmex.escape(
				__("Assistant is typing")
			)}</span><i></i><i></i><i></i></div>`;
			this.$.messages.appendChild(typing);
			this.scrollToEnd();
		}
		this.renderSuggestions();
	},

	scrollToEnd() {
		if (!this.$) return;
		requestAnimationFrame(() => {
			this.$.messages.scrollTop = this.$.messages.scrollHeight;
		});
	},

	autosize() {
		const input = this.$.input;
		input.style.height = "auto";
		input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
	},

	updateCounter() {
		const max = (this.config.limits && this.config.limits.max_message_length) || 2000;
		const length = this.$.input.value.length;
		const show = length > max * 0.8;
		this.$.count.hidden = !show;
		this.$.count.textContent = show ? `${length} / ${max}` : "";
		this.$.count.classList.toggle("is-over", length > max);
	},

	skeleton(rows) {
		return Array.from({ length: rows })
			.map((_, i) => `<div class="myrmex-skeleton myrmex-chat__skeleton" style="width:${[72, 54, 64][i % 3]}%"></div>`)
			.join("");
	},

	// --- sending ---------------------------------------------------------------

	submit() {
		const text = this.$.input.value.trim();
		if (!text || this.state.busy) return;
		const max = (this.config.limits && this.config.limits.max_message_length) || 2000;
		if (text.length > max) {
			frappe.show_alert({
				message: __("Your message is too long. Keep it under {0} characters.", [max]),
				indicator: "orange",
			});
			return;
		}
		this.$.input.value = "";
		this.autosize();
		this.updateCounter();
		this.send(text);
	},

	send(text) {
		this.showChat();
		const message = { role: "user", content: text };
		this.state.messages.push(message);
		this.appendBubble(message);
		this.persist();
		this.request(text);
	},

	request(text) {
		this.state.lastUserText = text;
		this.setBusy(true);

		const route = currentRoute();
		const context = {
			route,
			page_title: describeRoute(route).label,
			include_page: this.state.includePage ? 1 : 0,
		};

		const args = { message: text, context: JSON.stringify(context) };
		if (this.usesServerHistory()) {
			if (this.state.conversation) args.conversation = this.state.conversation;
		} else {
			const limit = (this.config.limits && this.config.limits.max_history_messages) || 20;
			// Everything before the message being sent, without error notices.
			const previous = this.state.messages.filter((m) => !m.error).slice(0, -1);
			args.history = JSON.stringify(
				previous.slice(-limit).map((m) => ({ role: m.role, content: m.content }))
			);
		}

		frappe.call({
			method: `${API}send_message`,
			type: "POST",
			args,
			callback: (r) => this.onReply(r.message || {}),
			error: () => this.onFailure(__("The assistant could not be reached. Check your connection.")),
		});
	},

	onReply(result) {
		this.setBusy(false);
		if (result.conversation) this.state.conversation = result.conversation;

		if (!result.ok) {
			const error = result.error || {};
			const final = ["too_long", "empty", "disabled", "conversation_full", "not_configured", "provider_auth", "not_found"];
			const retryable = !final.includes(error.code);
			this.onFailure(error.message || __("Something went wrong."), retryable);
			if (error.code === "conversation_full") this.offerNewConversation();
			this.persist();
			return;
		}

		const reply = { role: "assistant", content: result.message.content };
		this.state.messages.push(reply);
		this.appendBubble(reply);
		this.persist();
		this.scrollToEnd();

		if (!this.state.open) {
			this.state.unread = true;
			this.$.unread.hidden = false;
		}
	},

	onFailure(text, retry = true) {
		this.setBusy(false);
		const notice = { role: "assistant", content: text, error: true, retry };
		this.appendBubble(notice);
		this.scrollToEnd();
	},

	offerNewConversation() {
		const item = this.appendBubble({ role: "assistant", content: "", error: true });
		const bubble = item.querySelector(".myrmex-chat__bubble");
		bubble.textContent = "";
		const button = document.createElement("button");
		button.type = "button";
		button.className = "myrmex-chat__chip";
		button.textContent = __("Start a new conversation");
		button.addEventListener("click", () => this.newConversation());
		bubble.appendChild(button);
	},

	// --- history view ----------------------------------------------------------

	showChat() {
		this.state.view = "chat";
		this.$.history.hidden = true;
		this.$.messages.hidden = false;
		this.$.form.hidden = false;
		this.root.classList.remove("is-history");
		this.historyButton(false);
		this.updateContextChip();
		this.renderSuggestions();
	},

	showHistory() {
		if (!this.usesServerHistory()) {
			frappe.show_alert({
				message: __("Conversation history is turned off on this site."),
				indicator: "blue",
			});
			return;
		}
		this.state.view = "history";
		this.$.messages.hidden = true;
		this.$.form.hidden = true;
		this.$.context.hidden = true;
		this.$.suggestions.hidden = true;
		this.$.history.hidden = false;
		this.root.classList.add("is-history");
		this.historyButton(true);
		this.$.history.innerHTML = this.skeleton(4);

		frappe.call({
			method: `${API}list_conversations`,
			type: "GET",
			callback: (r) => this.renderHistory((r.message && r.message.conversations) || []),
			error: () => {
				this.$.history.innerHTML = `<p class="myrmex-chat__empty">${myrmex.escape(
					__("Could not load your conversations.")
				)}</p>`;
			},
		});
	},

	historyButton(active) {
		const button = this.root.querySelector("[data-action='history']");
		const label = active ? __("Back to conversation") : __("Conversation history");
		button.innerHTML = icon(active ? "back" : "history");
		button.setAttribute("aria-label", label);
		button.setAttribute("title", label);
	},

	renderHistory(conversations) {
		if (!conversations.length) {
			this.$.history.innerHTML = `
				<div class="myrmex-chat__empty">
					<p>${myrmex.escape(__("No saved conversations yet."))}</p>
					<button type="button" class="myrmex-chat__chip" data-history="new">${myrmex.escape(
						__("Start a conversation")
					)}</button>
				</div>`;
			return;
		}

		const rows = conversations
			.map(
				(c) => `
				<li class="myrmex-chat__history-item${c.name === this.state.conversation ? " is-current" : ""}">
					<button type="button" class="myrmex-chat__history-open" data-history="open"
						data-name="${myrmex.escape(c.name)}">
						<span class="myrmex-chat__history-title" dir="auto">${myrmex.escape(
							c.title || __("Untitled conversation")
						)}</span>
						<span class="myrmex-chat__history-meta">${myrmex.escape(
							c.last_message_at ? frappe.datetime.str_to_user(c.last_message_at) : ""
						)}</span>
					</button>
					<button type="button" class="myrmex-chat__icon-btn" data-history="delete"
						data-name="${myrmex.escape(c.name)}" aria-label="${myrmex.escape(
							__("Delete conversation")
						)}" title="${myrmex.escape(__("Delete conversation"))}">${icon("trash")}</button>
				</li>`
			)
			.join("");

		this.$.history.innerHTML = `
			<ul class="myrmex-chat__history-list">${rows}</ul>
			<button type="button" class="myrmex-chat__clear" data-history="clear">${myrmex.escape(
				__("Delete all conversations")
			)}</button>`;
	},

	onHistoryClick(event) {
		const target = event.target.closest("[data-history]");
		if (!target) return;
		const action = target.dataset.history;
		const name = target.dataset.name;

		if (action === "new") this.newConversation();
		if (action === "open") this.loadConversation(name);

		if (action === "delete") {
			frappe.confirm(__("Delete this conversation? This cannot be undone."), () => {
				frappe.call({
					method: `${API}delete_conversation`,
					type: "POST",
					args: { name },
					callback: () => {
						if (name === this.state.conversation) {
							this.state.conversation = null;
							this.state.messages = [];
							this.persist();
							this.renderMessages();
						}
						this.showHistory();
					},
				});
			});
		}

		if (action === "clear") {
			frappe.confirm(__("Delete all your conversations with the assistant?"), () => {
				frappe.call({
					method: `${API}clear_conversations`,
					type: "POST",
					callback: () => {
						this.state.conversation = null;
						this.state.messages = [];
						this.persist();
						this.renderMessages();
						this.showHistory();
					},
				});
			});
		}
	},
};

function clamp(value, low, high, fallback) {
	const number = parseInt(value, 10);
	if (Number.isNaN(number)) return fallback;
	return Math.max(low, Math.min(high, number));
}

/** Pick black or white text by WCAG contrast, mirroring the server helper. */
function readableOn(hex) {
	const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
	const linear = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
	const lum = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
	const dark = 0.0137; // luminance of #111827
	return 1.05 / (lum + 0.05) >= (Math.max(lum, dark) + 0.05) / (Math.min(lum, dark) + 0.05)
		? "#FFFFFF"
		: "#111827";
}

myrmex.chatbot._renderMarkdown = renderMarkdown;

// Start after Frappe's own startup: frappe.session and the user menu only
// exist once "app_ready" has fired (jQuery runs ready handlers asynchronously,
// so DOMContentLoaded is too early).
let started = false;
function start() {
	if (started || !window.frappe || !frappe.session || !frappe.session.user) return;
	started = true;
	myrmex.chatbot.init();
}
$(document).on("app_ready", start);
myrmex.ready(() => {
	if (document.getElementById("toolbar-user")) start();
});

export default myrmex.chatbot;
