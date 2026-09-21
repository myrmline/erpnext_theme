"""Who may use the assistant, how often, and with which settings.

Every entry point in chatbot.api goes through `require_access` first. It checks
the session, the enabled flag and the allowed roles, in that order, and raises
before any configuration or context is loaded.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

SETTINGS_DOCTYPE = "Chatbot Settings"

# Hard ceilings that apply whatever an administrator configures.
ABSOLUTE_MAX_MESSAGE_LENGTH = 8000
ABSOLUTE_MAX_HISTORY = 50
ABSOLUTE_MAX_CONVERSATIONS = 200
ABSOLUTE_MAX_MESSAGES_PER_CONVERSATION = 500


class ChatbotError(Exception):
	"""An expected failure with a message that is safe to show the user."""

	def __init__(self, code: str, message: str, http_status: int = 400):
		super().__init__(message)
		self.code = code
		self.message = message
		self.http_status = http_status

	def as_response(self) -> dict:
		return {"ok": False, "error": {"code": self.code, "message": self.message}}


def get_settings():
	"""The Single doc, or None while the DocType is not migrated yet."""
	try:
		return frappe.get_cached_doc(SETTINGS_DOCTYPE)
	except frappe.DoesNotExistError:
		return None
	except Exception:
		frappe.log_error(title="Myrmex Assistant: settings could not be loaded")
		return None


def limits(settings) -> dict:
	"""Configured limits, clamped to the absolute ceilings."""

	def bounded(field, default, low, high):
		value = cint(settings.get(field)) if settings else 0
		return max(low, min(high, value or default))

	return {
		"max_message_length": bounded("max_message_length", 2000, 50, ABSOLUTE_MAX_MESSAGE_LENGTH),
		"max_history_messages": bounded("max_history_messages", 20, 0, ABSOLUTE_MAX_HISTORY),
		"max_conversations": bounded("max_conversations", 30, 1, ABSOLUTE_MAX_CONVERSATIONS),
		"max_messages_per_conversation": bounded(
			"max_messages_per_conversation", 200, 10, ABSOLUTE_MAX_MESSAGES_PER_CONVERSATION
		),
		"rate_limit_per_minute": bounded("rate_limit_per_minute", 10, 1, 120),
		"rate_limit_per_day": bounded("rate_limit_per_day", 200, 1, 10000),
		"history_char_budget": 24000,
	}


def allowed_roles(settings) -> set[str]:
	return {row.role for row in (settings.get("allowed_roles") or []) if row.role}


def user_may_use(settings, user: str | None = None) -> bool:
	"""True when the assistant is on and this user holds an allowed role."""
	user = user or frappe.session.user
	if not settings or not cint(settings.enabled):
		return False
	if not user or user == "Guest":
		return False

	# Website users (customers, suppliers on the portal) never reach the Desk
	# assistant, whatever the role list says.
	if frappe.get_cached_value("User", user, "user_type") != "System User":
		return False

	roles = allowed_roles(settings)
	if not roles:
		return True
	return bool(roles.intersection(frappe.get_roles(user)))


def require_access():
	"""Raise unless the current session may use the assistant. Returns settings."""
	if frappe.session.user == "Guest":
		raise frappe.PermissionError(_("Please log in to use the assistant."))

	settings = get_settings()
	if not settings or not cint(settings.enabled):
		raise ChatbotError("disabled", _("The assistant is turned off."), 403)

	if not user_may_use(settings):
		raise frappe.PermissionError(_("You are not allowed to use the assistant."))

	return settings


def check_rate_limit(settings, user: str | None = None):
	"""Count one request against the per-minute and per-day windows.

	Uses the site's Redis cache. The key is namespaced per site by make_key, so
	benches that host several sites do not share counters.
	"""
	user = user or frappe.session.user
	configured = limits(settings)
	windows = (
		("minute", 60, configured["rate_limit_per_minute"]),
		("day", 86400, configured["rate_limit_per_day"]),
	)

	cache = frappe.cache()
	for label, seconds, allowed in windows:
		key = cache.make_key(f"myrmex_chatbot_rate:{label}:{user}")
		count = cache.incr(key)
		if count == 1:
			cache.expire(key, seconds)
		if count > allowed:
			if label == "minute":
				message = _("You're sending messages quickly. Wait a minute, then try again.")
			else:
				message = _("You've reached today's message limit. It resets within 24 hours.")
			raise ChatbotError("rate_limited", message, 429)


def assert_owner(conversation_name: str, user: str | None = None):
	"""Load a conversation and make sure it belongs to the caller.

	A conversation owned by someone else is reported as missing rather than
	forbidden, so its existence is not disclosed.
	"""
	user = user or frappe.session.user
	if not conversation_name or not isinstance(conversation_name, str):
		raise ChatbotError("not_found", _("That conversation no longer exists."), 404)

	owner = frappe.db.get_value("Chatbot Conversation", conversation_name, "user")
	if owner != user:
		raise ChatbotError("not_found", _("That conversation no longer exists."), 404)
	return frappe.get_doc("Chatbot Conversation", conversation_name)
