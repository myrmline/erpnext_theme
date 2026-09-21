// Theme Settings form: shortcuts to the visual editor and to the presets.

frappe.ui.form.on("Theme Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Open Theme Builder"), () => {
			frappe.set_route("theme-builder");
		});

		frm.page.set_primary_action(__("Save"), () => frm.save());

		frm.add_custom_button(
			__("Reset to Myrmex Default"),
			() => {
				frappe.confirm(__("Replace the current palette with Myrmex Default?"), () => {
					frappe.call({
						method: "theme_myrmex.api.reset_theme",
						freeze: true,
						freeze_message: __("Resetting theme"),
						callback: () => {
							frm.reload_doc();
							frappe.show_alert({ message: __("Theme reset"), indicator: "green" });
						},
					});
				});
			},
			__("Presets")
		);

		for (const preset of [
			"Myrmex Default",
			"Myrmex Blue",
			"Myrmex Dark",
			"Myrmex Minimal",
			"Myrmex Enterprise",
		]) {
			frm.add_custom_button(
				__(preset),
				() => {
					frappe.call({
						method: "theme_myrmex.api.apply_preset",
						args: { preset },
						callback: (r) => {
							if (!r.message) return;
							for (const [field, value] of Object.entries(r.message.settings)) {
								if (frm.get_field(field)) frm.set_value(field, value);
							}
							frm.set_value("theme_preset", preset);
							frappe.show_alert({
								message: __("{0} loaded — save to apply", [preset]),
								indicator: "blue",
							});
						},
					});
				},
				__("Presets")
			);
		}
	},

	enable_theme(frm) {
		if (!frm.doc.enable_theme) {
			frappe.show_alert({
				message: __("Myrmex styling stops after you save and reload."),
				indicator: "orange",
			});
		}
	},
});
