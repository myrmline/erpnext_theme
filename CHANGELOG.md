# Changelog

## 1.2.0

### Added
- **Table Styles** section in the Theme Builder and in Theme Settings: header
  background, text and weight, uppercase headers, row and stripe colours,
  selected row, hover mode (none, background tint, accent edge) and colour,
  border style, colour and width, table radius, row height, cell padding, and
  pagination style and alignment.
- The Theme Builder preview now includes a table, so the new settings are
  visible while editing, and settings groups can carry subheadings.
- Table styling in every shipped preset (Enterprise: uppercase headers and full
  borders; Minimal: compact rows and minimal pagination).
- French and Arabic translations for the new section.

### Changed
- List rows, report tables, datatables, child-table grids and plain tables all
  read the same table tokens, so one setting changes them together.
- Numeric theme values are clamped in one place, shared by the Theme Settings
  validation and the payload builder.
- "Striped table rows" moved from Components to Table Styles and is now
  "Striped rows". The stored value is unchanged.

### Fixed
- A striped row no longer covers the selected-row colour.

## 1.1.0

### Added
- **Myrmex Assistant**: permission-aware AI chat panel for Desk users, with
  OpenAI-compatible, Azure OpenAI and Anthropic providers; server-side context
  built with the user's permissions; history, retention, rate limits, role and
  page rules; suggested prompts; English, French and Arabic with RTL.
- DocTypes: Chatbot Settings, Chatbot Suggestion, Chatbot Conversation,
  Chatbot Message. Daily retention job; conversations removed with their user.
- `myrmex-states` stylesheet: skeletons, empty and error states, freeze overlay.
- Expanded token set: type scale, weights, derived radii, status text and soft
  colours, focus ring, layers, easing.
- French and Arabic translation files.
- Unit and integration tests.

### Changed
- Sidebar rewritten for the actual v15 markup (`.layout-side-section >
  .desk-sidebar`): workspace sidebar as a panel, sentence-case section labels,
  nested guide lines, rail with floating tooltips, restyled native mobile drawer.
- Navbar: translucent bar with scroll elevation, rail toggle only where it
  applies, restyled notification panel.
- Forms follow v15's single-card layout, with the tab bar joined to the card.
- Lists render as one card (filters, table, paging) instead of a card in a card.
- Workspace widgets, number cards and link cards refined; hover lift only on
  clickable shortcuts.
- Workspace decorations run inside the visible page only.

### Fixed
- Selecting *Automatic* dark mode no longer leaves the page without a palette
  (`frappe.ui.set_theme` was given `"automatic"` as a theme name).
- Frappe's default `desk_theme` of "Light" is no longer treated as a user choice.
- Ctrl+B no longer overrides bold formatting in text fields and editors.
- Breadcrumb styles now target v15's `#navbar-breadcrumbs`.
