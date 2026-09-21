import frappe

from theme_myrmex.install import ensure_chatbot_settings


def execute():
	"""Create Chatbot Settings with the default suggestions. The assistant stays off."""
	ensure_chatbot_settings()
	frappe.clear_cache(doctype="Chatbot Settings")
