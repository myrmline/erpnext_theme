// Theme Myrmex — Desk bundle entry.
// esbuild builds this into assets/theme_myrmex/dist/js/myrmex.bundle.js; the
// app_include_js hook loads it after Frappe's own bundles.
//
// Import order is the initialisation order: utils create the namespace, theme
// paints the variables, then the individual surfaces attach, and the
// assistant mounts last.

import "./myrmex-utils.js";
import "./myrmex-theme.js";
import "./myrmex-sidebar.js";
import "./myrmex-navbar.js";
import "./myrmex-workspace.js";
import "./myrmex-chatbot.js";
