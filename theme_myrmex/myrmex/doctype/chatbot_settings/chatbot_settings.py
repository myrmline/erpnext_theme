"""Chatbot Settings — configuration for the Myrmex Assistant.

Only System Manager can read or write this DocType. Browsers receive a filtered
copy through theme_myrmex.chatbot.service.public_config, which never contains
the provider, endpoint, model, key or system prompt.
"""

from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from theme_myrmex.chatbot.utils import parse_patterns

COLOR_FIELDS = ("primary_color", "chat_background", "user_message_color", "assistant_message_color")

BOUNDS = {
	"border_radius": (0, 32, 16),
	"panel_width": (320, 720, 400),
	"panel_height": (420, 960, 620),
	"max_history_messages": (0, 50, 20),
	"max_conversations": (1, 200, 30),
	"max_messages_per_conversation": (10, 500, 200),
	"retention_days": (0, 3650, 90),
	"max_context_fields": (5, 120, 40),
	"max_tokens": (64, 16000, 800),
	"request_timeout": (5, 180, 30),
	"max_message_length": (50, 8000, 2000),
	"rate_limit_per_minute": (1, 120, 10),
	"rate_limit_per_day": (1, 10000, 200),
}

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class ChatbotSettings(Document):
	def validate(self):
		self.apply_bounds()
		self.validate_colors()
		self.validate_endpoint()
		self.validate_patterns()
		self.validate_roles()
		self.validate_ready_to_enable()

	def on_update(self):
		frappe.clear_cache(doctype=self.doctype)
		# Every open Desk re-fetches its own filtered config; nothing sensitive
		# travels over the realtime channel.
		frappe.publish_realtime("myrmex_chatbot_updated", message={}, after_commit=True)

	def apply_bounds(self):
		for field, (low, high, default) in BOUNDS.items():
			raw = self.get(field)
			value = default if raw in (None, "") else cint(raw)
			self.set(field, max(low, min(high, value)))

		self.temperature = max(0.0, min(2.0, flt(self.temperature)))
		if self.ai_provider == "Anthropic" and self.temperature > 1:
			self.temperature = 1.0

	def validate_colors(self):
		for field in COLOR_FIELDS:
			value = (self.get(field) or "").strip()
			if not value:
				continue
			cleaned = value.lstrip("#")
			if len(cleaned) == 3:
				cleaned = "".join(char * 2 for char in cleaned)
			if len(cleaned) != 6 or any(char not in "0123456789abcdefABCDEF" for char in cleaned):
				frappe.throw(
					_("{0} is not a valid hex colour: {1}").format(_(self.meta.get_label(field)), value)
				)
			self.set(field, "#" + cleaned.upper())

	def validate_endpoint(self):
		endpoint = (self.api_endpoint or "").strip()
		self.api_endpoint = endpoint
		if not endpoint:
			if self.ai_provider == "Azure OpenAI":
				frappe.throw(_("Azure OpenAI needs the full chat completions URL as the API endpoint."))
			return

		parsed = urlparse(endpoint)
		if parsed.scheme not in ("http", "https") or not parsed.netloc:
			frappe.throw(_("The API endpoint must be a full http(s) URL."))
		if parsed.username or parsed.password:
			frappe.throw(_("Put credentials in the API key field, not in the endpoint URL."))
		if parsed.scheme == "http" and (parsed.hostname or "") not in LOCAL_HOSTS:
			frappe.msgprint(
				_("The API endpoint uses plain http. Messages and the API key will travel unencrypted."),
				indicator="orange",
				alert=True,
			)

	def validate_patterns(self):
		patterns = parse_patterns(self.page_patterns)
		if len(patterns) > 100:
			frappe.throw(_("Use at most 100 page patterns."))
		if self.page_visibility != "Everywhere" and not patterns:
			frappe.throw(_("Add at least one page pattern, or show the assistant everywhere."))

	def validate_roles(self):
		seen = set()
		for row in list(self.allowed_roles or []):
			if not row.role or row.role in seen:
				self.remove(row)
				continue
			seen.add(row.role)

	def validate_ready_to_enable(self):
		if not cint(self.enabled):
			return
		missing = []
		if not (self.model or "").strip():
			missing.append(_("Model"))
		if self.ai_provider != "OpenAI Compatible" and not self.api_key:
			missing.append(_("API key"))
		if missing:
			frappe.throw(
				_("Fill in {0} before enabling the assistant.").format(", ".join(missing)),
				title=_("Assistant not ready"),
			)
