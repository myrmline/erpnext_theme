"""Whitelisted endpoints and payload building for Theme Myrmex.

Every write goes through the normal permission stack: the caller must be able to
write "Theme Settings", which by default only System Manager can. Nothing here
touches an ERPNext document.
"""

import frappe
from frappe import _

from theme_myrmex.presets import (
	COLOR_VARIABLE_MAP,
	DARK_SURFACES,
	DEFAULTS,
	NUMBER_BOUNDS,
	PRESET_NAMES,
	PRESETS,
	SHADOWS,
	SIZE_VARIABLE_MAP,
	TABLE_BORDER_EDGES,
	TABLE_HEADER_WEIGHTS,
	TABLE_HOVER_MODES,
	TABLE_PAGINATION_ALIGN,
	TABLE_PAGINATION_STYLES,
)

CACHE_KEY = "myrmex_theme_payload"

# Fields that carry a unit when written to CSS.
PX_FIELDS = set(SIZE_VARIABLE_MAP.keys())



# Accent colours that survive the switch to dark mode.
DARK_SAFE_COLORS = (
	"primary_color",
	"secondary_color",
	"success_color",
	"warning_color",
	"error_color",
	"sidebar_active",
)


def get_settings() -> dict:
	"""Return Theme Settings as a plain dict, falling back to the defaults.

	Reads the Single doc without raising if the DocType has not been migrated
	yet, so a half-installed site still renders.
	"""
	values = DEFAULTS.copy()
	try:
		doc = frappe.get_cached_doc("Theme Settings")
	except Exception:
		return values

	for field in list(values.keys()):
		value = doc.get(field)
		if value not in (None, ""):
			values[field] = value

	values["custom_css"] = doc.get("custom_css") or ""
	return values


def build_payload(settings: dict | None = None) -> dict:
	"""Turn stored settings into the variable blocks the browser applies."""
	settings = settings or get_settings()

	light_vars = {}
	dark_vars = {}
	for field, variable in COLOR_VARIABLE_MAP.items():
		value = settings.get(field) or DEFAULTS.get(field)
		light_vars[variable] = value
		if field in DARK_SAFE_COLORS:
			dark_vars[variable] = value

	# Derived light tokens.
	light_vars["--myrmex-surface-alt"] = _mix(settings.get("background_color"), "#FFFFFF", 0.5)
	light_vars["--myrmex-primary-soft"] = _with_alpha(settings.get("primary_color"), 0.10)
	light_vars["--myrmex-primary-contrast"] = _readable_on(settings.get("primary_color"))

	dark_vars.update(DARK_SURFACES)
	dark_vars["--myrmex-sidebar-icon"] = DARK_SURFACES["--myrmex-muted"]
	dark_vars["--myrmex-primary-soft"] = _with_alpha(settings.get("primary_color"), 0.18)
	dark_vars["--myrmex-primary-contrast"] = _readable_on(settings.get("primary_color"))
	# The selected row keeps the brand colour in dark mode, as a tint.
	dark_vars["--myrmex-table-selected-bg"] = _with_alpha(settings.get("primary_color"), 0.22)

	shared_vars = {}
	for field, variable in SIZE_VARIABLE_MAP.items():
		value = _number(settings, field)
		shared_vars[variable] = f"{value}px" if field in PX_FIELDS else str(value)

	shared_vars.update(_table_vars(settings))
	shared_vars.update(SHADOWS.get(settings.get("shadow_size") or "Medium", SHADOWS["Medium"]))
	shared_vars["--myrmex-transition"] = (
		"150ms ease" if frappe.utils.cint(settings.get("enable_animations")) else "0ms linear"
	)

	return {
		"enabled": bool(frappe.utils.cint(settings.get("enable_theme"))),
		"table": {
			"hover": TABLE_HOVER_MODES.get(
				settings.get("table_hover_effect") or "", TABLE_HOVER_MODES["Background tint"]
			),
			"pagination": TABLE_PAGINATION_STYLES.get(
				settings.get("table_pagination_style") or "", TABLE_PAGINATION_STYLES["Pills"]
			),
		},
		"appearance": settings.get("default_appearance") or "System",
		"density": settings.get("density") or "Comfortable",
		"zebra_tables": bool(frappe.utils.cint(settings.get("zebra_tables"))),
		"collapse_sidebar_by_default": bool(
			frappe.utils.cint(settings.get("collapse_sidebar_by_default"))
		),
		"preset": settings.get("theme_preset") or "Myrmex Default",
		"vars": light_vars,
		"dark_vars": dark_vars,
		"shared_vars": shared_vars,
		"custom_css": settings.get("custom_css") or "",
	}


def _number(settings: dict, field: str) -> int:
	"""Read a numeric setting, falling back to the default and clamping it."""
	value = settings.get(field)
	if value in (None, ""):
		value = DEFAULTS.get(field, 0)
	try:
		number = int(float(value))
	except (TypeError, ValueError):
		number = int(DEFAULTS.get(field, 0) or 0)

	low, high = NUMBER_BOUNDS.get(field, (None, None))
	if low is not None:
		number = max(low, min(high, number))
	return number


def _table_vars(settings: dict) -> dict:
	"""Table settings that are values rather than colours or plain sizes."""
	width = _number(settings, "table_border_width")
	edges = TABLE_BORDER_EDGES.get(
		settings.get("table_border_style") or "", TABLE_BORDER_EDGES["Horizontal lines"]
	)
	uppercase = frappe.utils.cint(settings.get("table_header_uppercase"))

	return {
		# Row rules and cell separators are separate, so "Horizontal lines" is
		# one variable set to 0 rather than a different rule.
		"--myrmex-table-row-border-width": f"{width if 'row' in edges else 0}px",
		"--myrmex-table-cell-border-width": f"{width if 'cell' in edges else 0}px",
		"--myrmex-table-header-weight": TABLE_HEADER_WEIGHTS.get(
			settings.get("table_header_weight") or "", TABLE_HEADER_WEIGHTS["Semibold"]
		),
		"--myrmex-table-header-transform": "uppercase" if uppercase else "none",
		"--myrmex-table-header-tracking": "0.04em" if uppercase else "0",
		"--myrmex-table-paging-justify": TABLE_PAGINATION_ALIGN.get(
			settings.get("table_pagination_align") or "", TABLE_PAGINATION_ALIGN["Edges"]
		),
	}


def get_theme_payload() -> dict:
	"""Cached payload used by boot and by the website context."""
	cached = frappe.cache().get_value(CACHE_KEY)
	if cached:
		return cached

	payload = build_payload()
	frappe.cache().set_value(CACHE_KEY, payload)
	return payload


def clear_theme_cache(doc=None, method=None):
	"""Drop the cache and push the new palette to every open session."""
	frappe.cache().delete_value(CACHE_KEY)
	frappe.clear_cache(doctype="Theme Settings")

	try:
		frappe.publish_realtime(
			"myrmex_theme_updated",
			message=build_payload(),
			after_commit=True,
		)
	except Exception:
		# Realtime is a convenience, never a requirement.
		frappe.log_error(title="Theme Myrmex: realtime publish failed")


# ---------------------------------------------------------------------------
# Whitelisted endpoints
# ---------------------------------------------------------------------------


@frappe.whitelist(allow_guest=True)
def get_theme() -> dict:
	"""Read the active theme. Guest-readable so the login page can style itself.

	Only presentation tokens are returned; no document data is exposed.
	"""
	return get_theme_payload()


@frappe.whitelist()
def get_settings_and_presets() -> dict:
	"""Everything the Theme Builder needs in one call."""
	frappe.only_for("System Manager")
	return {
		"settings": get_settings(),
		"presets": PRESET_NAMES,
		"defaults": DEFAULTS,
	}


@frappe.whitelist()
def save_theme(values: str | dict) -> dict:
	"""Persist the Theme Builder form. Permission-checked by Frappe on save."""
	values = frappe.parse_json(values) or {}

	doc = frappe.get_doc("Theme Settings")
	doc.check_permission("write")

	allowed = set(DEFAULTS.keys()) | {"custom_css"}
	for field, value in values.items():
		if field in allowed:
			doc.set(field, value)

	doc.save()
	frappe.msgprint(_("Theme saved"), alert=True, indicator="green")
	return build_payload()


@frappe.whitelist()
def apply_preset(preset: str) -> dict:
	"""Load a shipped preset into Theme Settings without saving it yet."""
	frappe.only_for("System Manager")
	if preset not in PRESETS:
		frappe.throw(_("Unknown preset: {0}").format(preset))

	return {"settings": PRESETS[preset], "payload": build_payload(PRESETS[preset])}


@frappe.whitelist()
def reset_theme() -> dict:
	"""Restore the Myrmex Default palette and save it."""
	return save_theme(PRESETS["Myrmex Default"])


@frappe.whitelist()
def preview_payload(values: str | dict) -> dict:
	"""Build a payload from unsaved values, for the live preview."""
	frappe.only_for("System Manager")
	values = frappe.parse_json(values) or {}
	settings = DEFAULTS.copy()
	settings.update({k: v for k, v in values.items() if k in settings or k == "custom_css"})
	return build_payload(settings)


# ---------------------------------------------------------------------------
# Small colour helpers (no external dependency)
# ---------------------------------------------------------------------------


def _to_rgb(value: str | None):
	value = (value or "").strip().lstrip("#")
	if len(value) == 3:
		value = "".join(char * 2 for char in value)
	if len(value) != 6:
		return None
	try:
		return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))
	except ValueError:
		return None


def _with_alpha(color: str | None, alpha: float) -> str:
	rgb = _to_rgb(color) or (29, 161, 242)
	return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"


def _mix(color_a: str | None, color_b: str | None, weight: float) -> str:
	first = _to_rgb(color_a) or (255, 255, 255)
	second = _to_rgb(color_b) or (255, 255, 255)
	mixed = [round(first[i] * (1 - weight) + second[i] * weight) for i in range(3)]
	return "#{:02X}{:02X}{:02X}".format(*mixed)


def _luminance(color: str | None) -> float:
	"""WCAG relative luminance."""
	rgb = _to_rgb(color) or (29, 161, 242)
	channels = []
	for channel in rgb:
		value = channel / 255
		channels.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
	return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _readable_on(color: str | None) -> str:
	"""Pick the foreground that actually has more contrast on this background.

	Comparing real WCAG contrast ratios rather than testing luminance against a
	threshold: mid-tone accents such as amber score badly against white, and a
	threshold picks the wrong side of them.
	"""
	background = _luminance(color)
	dark = _luminance("#111827")

	white_ratio = 1.05 / (background + 0.05)
	dark_ratio = (max(background, dark) + 0.05) / (min(background, dark) + 0.05)

	return "#FFFFFF" if white_ratio >= dark_ratio else "#111827"
