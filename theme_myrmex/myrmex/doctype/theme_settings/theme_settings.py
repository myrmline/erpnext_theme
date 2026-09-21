"""Theme Settings — the stored configuration for Theme Myrmex.

A Single DocType. It holds presentation values only; no business data and no
permission flags. Saving it clears the cached payload and pushes the new palette
to every open session (see theme_myrmex.api.clear_theme_cache, wired through the
doc_events hook).
"""

import frappe
from frappe import _
from frappe.model.document import Document

from theme_myrmex.presets import CHOICE_FIELDS, COLOR_VARIABLE_MAP, DEFAULTS, NUMBER_BOUNDS


class ThemeSettings(Document):
	def validate(self):
		self.normalise_colors()
		self.apply_sensible_bounds()
		self.flag_custom_preset()

	def normalise_colors(self):
		"""Accept #abc, abc123 or #ABC123 and store a consistent #RRGGBB."""
		for field in COLOR_VARIABLE_MAP:
			value = (self.get(field) or "").strip()
			if not value:
				self.set(field, DEFAULTS.get(field))
				continue

			cleaned = value.lstrip("#")
			if len(cleaned) == 3:
				cleaned = "".join(char * 2 for char in cleaned)

			if len(cleaned) != 6 or any(char not in "0123456789abcdefABCDEF" for char in cleaned):
				frappe.throw(
					_("{0} is not a valid hex colour: {1}").format(_(self.meta.get_label(field)), value)
				)

			self.set(field, "#" + cleaned.upper())

	def apply_sensible_bounds(self):
		"""Keep sizes inside a range that still produces a usable Desk."""
		for field, (low, high) in NUMBER_BOUNDS.items():
			value = frappe.utils.cint(self.get(field)) or frappe.utils.cint(DEFAULTS.get(field))
			self.set(field, max(low, min(high, value)))

	def flag_custom_preset(self):
		"""If the values no longer match the chosen preset, call it Custom."""
		from theme_myrmex.presets import PRESETS

		preset = PRESETS.get(self.theme_preset)
		if not preset:
			return

		tracked = list(COLOR_VARIABLE_MAP) + list(NUMBER_BOUNDS) + list(CHOICE_FIELDS)
		for field in tracked:
			stored = self.get(field)
			expected = preset.get(field)
			if isinstance(expected, int):
				if frappe.utils.cint(stored) != expected:
					self.theme_preset = "Custom"
					return
			elif (stored or "") != (expected or ""):
				self.theme_preset = "Custom"
				return
