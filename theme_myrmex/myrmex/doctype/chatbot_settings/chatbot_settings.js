// Chatbot Settings form: connection test, provider hints, default suggestions.

const MYRMEX_ENDPOINT_HINTS = {
	"OpenAI Compatible": "https://api.openai.com/v1/chat/completions",
	"Azure OpenAI":
		"https://<resource>.openai.azure.com/openai/deployments/<deployment>/chat/completions?api-version=<version>",
	Anthropic: "https://api.anthropic.com/v1/messages",
};

frappe.ui.form.on("Chatbot Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Test connection"), () => myrmexTestConnection(frm));

		frm.add_custom_button(
			__("Restore default suggestions"),
			() => {
				frappe.confirm(__("Replace the suggestion table with the default prompts?"), () => {
					frappe.call({
						method: "theme_myrmex.install.default_chatbot_suggestions",
						callback: (r) => {
							frm.clear_table("suggestions");
							(r.message || []).forEach((row) => frm.add_child("suggestions", row));
							frm.refresh_field("suggestions");
							frm.dirty();
						},
					});
				});
			},
			__("Actions")
		);

		frm.add_custom_button(
			__("View conversations"),
			() => frappe.set_route("List", "Chatbot Conversation"),
			__("Actions")
		);

		myrmexSetEndpointPlaceholder(frm);
	},

	ai_provider(frm) {
		myrmexSetEndpointPlaceholder(frm);
	},

	enabled(frm) {
		if (frm.doc.enabled && !frm.doc.model) {
			frappe.show_alert({
				message: __("Set a model and test the connection before saving."),
				indicator: "orange",
			});
		}
	},
});

function myrmexSetEndpointPlaceholder(frm) {
	const field = frm.get_field("api_endpoint");
	if (!field || !field.$input) return;
	field.$input.attr("placeholder", MYRMEX_ENDPOINT_HINTS[frm.doc.ai_provider] || "");
}

function myrmexTestConnection(frm) {
	const run = () =>
		frappe.call({
			method: "theme_myrmex.chatbot.api.test_connection",
			freeze: true,
			freeze_message: __("Contacting the AI provider"),
			callback: (r) => {
				const result = r.message || {};
				if (result.ok) {
					frappe.msgprint({
						title: __("Connection works"),
						indicator: "green",
						message: __("{0} answered in {1} ms using {2}.", [
							frappe.utils.escape_html(result.provider),
							result.latency_ms,
							frappe.utils.escape_html(result.model),
						]),
					});
				} else {
					frappe.msgprint({
						title: __("Connection failed"),
						indicator: "red",
						message: frappe.utils.escape_html(
							(result.error && result.error.message) || __("Unknown error")
						),
					});
				}
			},
		});

	// The test uses the saved settings, so save first if anything changed.
	if (frm.is_dirty()) {
		frm.save().then(run);
	} else {
		run();
	}
}
