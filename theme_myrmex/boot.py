"""Deliver the theme and the assistant config with the page instead of after it."""

import frappe

from theme_myrmex.api import get_theme_payload


def boot_session(bootinfo):
	"""extend_bootinfo hook: attach the palette and the assistant config."""
	try:
		bootinfo.myrmex_theme = get_theme_payload()
	except Exception:
		# A broken theme must never block the Desk from booting.
		frappe.log_error(title="Theme Myrmex: bootinfo failed")

	try:
		from theme_myrmex.chatbot.service import public_config

		# Filtered per user; contains no provider details or secrets.
		bootinfo.myrmex_chatbot = public_config()
	except Exception:
		bootinfo.myrmex_chatbot = {"enabled": False}
		frappe.log_error(title="Myrmex Assistant: bootinfo failed")


def update_website_context(context):
	"""Make the palette available to portal and login templates."""
	try:
		context.myrmex_theme = get_theme_payload()
	except Exception:
		context.myrmex_theme = None
	return context
