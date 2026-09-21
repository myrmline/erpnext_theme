// Theme Myrmex — website / login bundle.
//
// Outside the Desk there is no frappe.boot, so the palette is fetched once from
// the guest-readable endpoint. Only presentation tokens travel over this call.

(function () {
	const ROOT = document.documentElement;
	ROOT.classList.add("myrmex-web");

	function applyVariables(payload) {
		if (!payload || !payload.enabled) {
			ROOT.classList.remove("myrmex-web");
			return;
		}

		const blocks = [
			[":root", payload.shared_vars],
			[':root:not([data-theme="dark"])', payload.vars],
			['[data-theme="dark"]', payload.dark_vars],
		];

		const css = blocks
			.filter(([, vars]) => vars && Object.keys(vars).length)
			.map(([selector, vars]) => {
				const body = Object.entries(vars)
					.map(([name, value]) => `\t${name}: ${value};`)
					.join("\n");
				return `${selector} {\n${body}\n}`;
			})
			.join("\n\n");

		let style = document.getElementById("myrmex-theme-vars");
		if (!style) {
			style = document.createElement("style");
			style.id = "myrmex-theme-vars";
			document.head.appendChild(style);
		}
		style.textContent = css + (payload.custom_css ? `\n\n${payload.custom_css}` : "");
	}

	fetch("/api/method/theme_myrmex.api.get_theme", {
		headers: { Accept: "application/json" },
		credentials: "same-origin",
	})
		.then((response) => (response.ok ? response.json() : null))
		.then((data) => data && applyVariables(data.message))
		.catch(() => {
			// Falling back to the CSS defaults is a perfectly good login page.
		});
})();
