"""Theme tokens, the field -> CSS variable map, and the shipped presets.

Everything the browser needs is derived from here, so adding a token means
touching exactly one file: add the field to the Theme Settings DocType, add the
mapping below, and use the variable in CSS.
"""

# Colour fields -> CSS custom property. These are re-emitted per colour scheme.
COLOR_VARIABLE_MAP = {
	"primary_color": "--myrmex-primary",
	"secondary_color": "--myrmex-secondary",
	"background_color": "--myrmex-background",
	"surface_color": "--myrmex-surface",
	"text_color": "--myrmex-text",
	"muted_text_color": "--myrmex-muted",
	"border_color": "--myrmex-border",
	"success_color": "--myrmex-success",
	"warning_color": "--myrmex-warning",
	"error_color": "--myrmex-error",
	"sidebar_background": "--myrmex-sidebar-background",
	"sidebar_text": "--myrmex-sidebar-text",
	"sidebar_active": "--myrmex-sidebar-active",
	"sidebar_hover": "--myrmex-sidebar-hover",
	"sidebar_icon": "--myrmex-sidebar-icon",
	"navbar_background": "--myrmex-navbar-background",
	"navbar_text": "--myrmex-navbar-text",
	"navbar_border": "--myrmex-navbar-border",
	"navbar_search_background": "--myrmex-navbar-search-background",
	"table_header_background": "--myrmex-table-header-bg",
	"table_header_text": "--myrmex-table-header-text",
	"table_row_background": "--myrmex-table-row-bg",
	"table_row_text": "--myrmex-table-row-text",
	"table_stripe_background": "--myrmex-table-stripe-bg",
	"table_row_hover": "--myrmex-table-hover-bg",
	"table_selected_background": "--myrmex-table-selected-bg",
	"table_border_color": "--myrmex-table-border",
}

# Numeric fields -> CSS custom property. Emitted once, shared by both schemes.
SIZE_VARIABLE_MAP = {
	"sidebar_width": "--myrmex-sidebar-width",
	"navbar_height": "--myrmex-navbar-height",
	"card_radius": "--myrmex-card-radius",
	"button_radius": "--myrmex-button-radius",
	"input_radius": "--myrmex-input-radius",
	"card_padding": "--myrmex-card-padding",
	"table_radius": "--myrmex-table-radius",
	"table_row_height": "--myrmex-table-row-height",
	"table_cell_padding": "--myrmex-table-cell-padding",
}

SHADOWS = {
	"None": {
		"--myrmex-shadow": "none",
		"--myrmex-shadow-hover": "none",
		"--myrmex-shadow-lg": "none",
	},
	"Small": {
		"--myrmex-shadow": "0 1px 2px rgba(16, 24, 40, 0.06)",
		"--myrmex-shadow-hover": "0 2px 6px rgba(16, 24, 40, 0.10)",
		"--myrmex-shadow-lg": "0 6px 16px rgba(16, 24, 40, 0.12)",
	},
	"Medium": {
		"--myrmex-shadow": "0 1px 3px rgba(16, 24, 40, 0.08), 0 1px 2px rgba(16, 24, 40, 0.04)",
		"--myrmex-shadow-hover": "0 6px 16px rgba(16, 24, 40, 0.12)",
		"--myrmex-shadow-lg": "0 16px 40px rgba(16, 24, 40, 0.16)",
	},
	"Large": {
		"--myrmex-shadow": "0 4px 10px rgba(16, 24, 40, 0.10)",
		"--myrmex-shadow-hover": "0 10px 28px rgba(16, 24, 40, 0.16)",
		"--myrmex-shadow-lg": "0 24px 56px rgba(16, 24, 40, 0.22)",
	},
}

# Sane ranges for the numeric fields, shared by the Theme Settings validation
# and by payload building, so a value typed into the form and a value set by a
# script are clamped the same way.
NUMBER_BOUNDS = {
	"sidebar_width": (180, 380),
	"navbar_height": (48, 88),
	"card_radius": (0, 32),
	"button_radius": (0, 32),
	"input_radius": (0, 32),
	"card_padding": (8, 40),
	"table_radius": (0, 24),
	"table_row_height": (28, 64),
	"table_cell_padding": (4, 28),
	"table_border_width": (0, 3),
}

# Non-colour, non-numeric fields that still change how the Desk looks. Used to
# tell whether the saved values still match the chosen preset.
CHOICE_FIELDS = (
	"shadow_size",
	"density",
	"table_header_weight",
	"table_header_uppercase",
	"table_hover_effect",
	"table_border_style",
	"table_pagination_style",
	"table_pagination_align",
	"zebra_tables",
)

# Header weight choices, as font-weight values.
TABLE_HEADER_WEIGHTS = {
	"Regular": "420",
	"Medium": "500",
	"Semibold": "600",
}

# Which edges the border width applies to. "Horizontal lines" keeps the row
# rules and drops the cell separators, which is the default table look.
TABLE_BORDER_EDGES = {
	"All borders": ("row", "cell"),
	"Horizontal lines": ("row",),
	"None": (),
}

# justify-content for the pagination bar. "Edges" keeps Frappe's own split of
# page-size buttons on one side and "Load more" on the other.
TABLE_PAGINATION_ALIGN = {
	"Edges": "space-between",
	"Left": "flex-start",
	"Centre": "center",
	"Right": "flex-end",
}

# Values written to data attributes on <html> for the rules that need a
# selector rather than a variable.
TABLE_HOVER_MODES = {
	"None": "none",
	"Background tint": "tint",
	"Accent edge": "accent",
}

TABLE_PAGINATION_STYLES = {
	"Pills": "pills",
	"Buttons": "buttons",
	"Minimal": "minimal",
}

# Surfaces used when the Desk is in dark mode. Accent colours (primary,
# secondary, success, warning, error) are carried over from the user's palette,
# so a custom brand colour stays recognisable in dark mode.
DARK_SURFACES = {
	"--myrmex-background": "#0F1117",
	"--myrmex-surface": "#171A21",
	"--myrmex-surface-alt": "#1C202A",
	"--myrmex-text": "#E5E7EB",
	"--myrmex-muted": "#9AA3B2",
	"--myrmex-border": "#272D3A",
	"--myrmex-sidebar-background": "#12151C",
	"--myrmex-sidebar-text": "#D7DCE5",
	"--myrmex-sidebar-hover": "rgba(255, 255, 255, 0.06)",
	"--myrmex-navbar-background": "#12151C",
	"--myrmex-navbar-text": "#E5E7EB",
	"--myrmex-navbar-border": "#272D3A",
	"--myrmex-navbar-search-background": "#1C202A",
	# Table colours follow the dark surfaces too: a light custom header or row
	# colour would be unreadable here. The accent-derived selected row is
	# rebuilt from the user's primary colour in api.build_payload.
	"--myrmex-table-header-bg": "#1C202A",
	"--myrmex-table-header-text": "#9AA3B2",
	"--myrmex-table-row-bg": "#171A21",
	"--myrmex-table-row-text": "#E5E7EB",
	"--myrmex-table-stripe-bg": "#1B2029",
	"--myrmex-table-hover-bg": "#1F2430",
	"--myrmex-table-border": "#272D3A",
}

# The Myrmex Default palette doubles as the fallback for any empty field.
DEFAULTS = {
	"enable_theme": 1,
	"theme_preset": "Myrmex Default",
	"default_appearance": "System",
	"density": "Comfortable",
	"enable_animations": 1,
	"zebra_tables": 0,
	"collapse_sidebar_by_default": 0,
	"primary_color": "#1DA1F2",
	"secondary_color": "#1426A9",
	"background_color": "#F7F7F9",
	"surface_color": "#FFFFFF",
	"text_color": "#111827",
	"muted_text_color": "#6B7280",
	"border_color": "#E5E7EB",
	"success_color": "#22C55E",
	"warning_color": "#F59E0B",
	"error_color": "#EF4444",
	"sidebar_background": "#FFFFFF",
	"sidebar_text": "#111827",
	"sidebar_active": "#1DA1F2",
	"sidebar_hover": "#F1F5F9",
	"sidebar_icon": "#6B7280",
	"navbar_background": "#FFFFFF",
	"navbar_text": "#111827",
	"navbar_border": "#E5E7EB",
	"navbar_search_background": "#F3F4F6",
	"sidebar_width": 260,
	"navbar_height": 60,
	"card_radius": 14,
	"button_radius": 8,
	"input_radius": 8,
	"card_padding": 20,
	"shadow_size": "Medium",
	"table_header_background": "#FBFBFC",
	"table_header_text": "#6B7280",
	"table_header_weight": "Semibold",
	"table_header_uppercase": 0,
	"table_row_background": "#FFFFFF",
	"table_row_text": "#111827",
	"table_stripe_background": "#F8F8FA",
	"table_row_hover": "#F6F7F9",
	"table_selected_background": "#E8F5FE",
	"table_hover_effect": "Background tint",
	"table_border_style": "Horizontal lines",
	"table_border_color": "#E5E7EB",
	"table_border_width": 1,
	"table_radius": 10,
	"table_row_height": 42,
	"table_cell_padding": 16,
	"table_pagination_style": "Pills",
	"table_pagination_align": "Edges",
}


def _preset(**overrides):
	values = DEFAULTS.copy()
	values.update(overrides)
	return values


PRESETS = {
	"Myrmex Default": _preset(),
	"Myrmex Blue": _preset(
		theme_preset="Myrmex Blue",
		primary_color="#2563EB",
		secondary_color="#1E3A8A",
		background_color="#F4F7FE",
		sidebar_background="#FFFFFF",
		sidebar_active="#2563EB",
		sidebar_hover="#EEF3FF",
		navbar_search_background="#EEF3FF",
		card_radius=16,
		button_radius=10,
		input_radius=10,
		table_header_background="#F7FAFF",
		table_row_hover="#EEF3FF",
		table_stripe_background="#F9FBFF",
		table_selected_background="#E3ECFF",
		table_border_color="#E3E8F4",
		table_radius=12,
	),
	"Myrmex Dark": _preset(
		theme_preset="Myrmex Dark",
		default_appearance="Dark",
		primary_color="#38BDF8",
		secondary_color="#818CF8",
		background_color="#0F1117",
		surface_color="#171A21",
		text_color="#E5E7EB",
		muted_text_color="#9AA3B2",
		border_color="#272D3A",
		sidebar_background="#12151C",
		sidebar_text="#D7DCE5",
		sidebar_active="#38BDF8",
		sidebar_hover="#1C202A",
		sidebar_icon="#9AA3B2",
		navbar_background="#12151C",
		navbar_text="#E5E7EB",
		navbar_border="#272D3A",
		navbar_search_background="#1C202A",
		table_header_background="#1C202A",
		table_header_text="#9AA3B2",
		table_row_background="#171A21",
		table_row_text="#E5E7EB",
		table_stripe_background="#1B2029",
		table_row_hover="#1F2430",
		table_selected_background="#1E3A4C",
		table_border_color="#272D3A",
	),
	"Myrmex Minimal": _preset(
		theme_preset="Myrmex Minimal",
		primary_color="#111827",
		secondary_color="#374151",
		background_color="#FFFFFF",
		surface_color="#FFFFFF",
		border_color="#E7E7E9",
		sidebar_background="#FFFFFF",
		sidebar_active="#111827",
		sidebar_hover="#F4F4F5",
		navbar_search_background="#F4F4F5",
		card_radius=8,
		button_radius=6,
		input_radius=6,
		card_padding=16,
		shadow_size="None",
		density="Compact",
		table_header_background="#FFFFFF",
		table_stripe_background="#FAFAFA",
		table_row_hover="#F4F4F5",
		table_selected_background="#EFEFF1",
		table_border_color="#E7E7E9",
		table_border_width=1,
		table_radius=6,
		table_row_height=36,
		table_cell_padding=12,
		table_pagination_style="Minimal",
	),
	"Myrmex Enterprise": _preset(
		theme_preset="Myrmex Enterprise",
		primary_color="#0F62FE",
		secondary_color="#0043CE",
		background_color="#F2F4F8",
		text_color="#161616",
		border_color="#DDE1E6",
		sidebar_background="#161C2D",
		sidebar_text="#C9D1E4",
		sidebar_active="#0F62FE",
		sidebar_hover="#212942",
		sidebar_icon="#8D97B0",
		navbar_background="#FFFFFF",
		navbar_search_background="#F2F4F8",
		card_radius=10,
		button_radius=6,
		input_radius=6,
		shadow_size="Small",
		table_header_background="#F2F4F8",
		table_header_text="#4D5358",
		table_header_uppercase=1,
		table_row_hover="#EDF1F8",
		table_stripe_background="#F7F9FC",
		table_selected_background="#D9E7FF",
		table_border_style="All borders",
		table_border_color="#DDE1E6",
		table_radius=4,
		table_row_height=38,
		table_cell_padding=14,
		table_pagination_style="Buttons",
	),
}

PRESET_NAMES = list(PRESETS.keys())
