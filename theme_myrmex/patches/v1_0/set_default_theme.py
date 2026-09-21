import frappe

from theme_myrmex.install import ensure_theme_settings


def execute():
	"""Make sure Theme Settings exists and holds the default preset."""
	ensure_theme_settings()
	frappe.clear_cache()
