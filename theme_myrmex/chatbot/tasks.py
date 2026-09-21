"""Scheduled jobs for the assistant."""

import frappe
from frappe.utils import add_days, cint, now_datetime

from theme_myrmex.chatbot.security import get_settings


def delete_expired_conversations():
	"""Daily: remove conversations idle for longer than the retention period.

	A retention of 0 keeps conversations until users delete them.
	"""
	settings = get_settings()
	days = cint(settings.get("retention_days")) if settings else 0
	if days <= 0:
		return

	cutoff = add_days(now_datetime(), -days)
	expired = frappe.get_all(
		"Chatbot Conversation",
		filters={"last_message_at": ("<", cutoff)},
		pluck="name",
		limit_page_length=5000,
	)
	for name in expired:
		frappe.delete_doc("Chatbot Conversation", name, ignore_permissions=True, force=True)

	if expired:
		frappe.db.commit()


def delete_user_conversations(doc, method=None):
	"""doc_events User.on_trash: remove the deleted user's assistant history."""
	names = frappe.get_all("Chatbot Conversation", filters={"user": doc.name}, pluck="name")
	if names:
		frappe.db.delete("Chatbot Message", {"conversation": ("in", names)})
		frappe.db.delete("Chatbot Conversation", {"name": ("in", names)})
