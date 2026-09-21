"""Whitelisted chatbot endpoints.

Frappe's convention is /api/method/<dotted.path>, so the REST-style routes in
the brief map to:

	GET    /api/chatbot/config                -> get_config
	GET    /api/chatbot/conversations         -> list_conversations
	GET    /api/chatbot/conversations/:id     -> get_conversation
	DELETE /api/chatbot/conversations/:id     -> delete_conversation   (POST)
	POST   /api/chatbot/messages              -> send_message

All of them are login-only (no allow_guest). Expected failures come back as
{"ok": false, "error": {"code", "message"}} with HTTP 200 so the chat panel can
show them inline instead of Frappe's modal error dialog. Authorisation failures
still raise PermissionError.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from theme_myrmex.chatbot import providers, service
from theme_myrmex.chatbot.security import (
	ChatbotError,
	assert_owner,
	check_rate_limit,
	get_settings,
	limits,
	require_access,
)


def _guard(fn, *args, **kwargs):
	try:
		return fn(*args, **kwargs)
	except ChatbotError as error:
		# Returned, not raised: Frappe commits normally, so bookkeeping written
		# before the failure (the user's stored turn) is kept on purpose.
		response = error.as_response()
		conversation = getattr(error, "conversation", None)
		if conversation:
			response["conversation"] = conversation
		return response


@frappe.whitelist(methods=["GET"])
def get_config() -> dict:
	"""Presentation and behaviour settings for the current user. No secrets."""
	return service.public_config()


@frappe.whitelist(methods=["POST"])
def send_message(message: str, conversation: str | None = None, context=None, history=None) -> dict:
	"""Send one user message and return the assistant's reply."""

	def run():
		settings = require_access()
		check_rate_limit(settings)
		return service.send_message(settings, message, conversation, context, history)

	return _guard(run)


@frappe.whitelist(methods=["GET"])
def list_conversations() -> dict:
	def run():
		settings = require_access()
		if not cint(settings.enable_history):
			return {"ok": True, "conversations": []}
		return {
			"ok": True,
			"conversations": service.list_conversations(
				frappe.session.user, limits(settings)["max_conversations"]
			),
		}

	return _guard(run)


@frappe.whitelist(methods=["GET"])
def get_conversation(name: str) -> dict:
	def run():
		settings = require_access()
		doc = assert_owner(name)
		return {
			"ok": True,
			"conversation": {"name": doc.name, "title": doc.title},
			"messages": service.conversation_messages(
				doc.name, limits(settings)["max_messages_per_conversation"]
			),
		}

	return _guard(run)


@frappe.whitelist(methods=["POST"])
def delete_conversation(name: str) -> dict:
	def run():
		require_access()
		doc = assert_owner(name)
		service.delete_conversation(doc.name)
		return {"ok": True}

	return _guard(run)


@frappe.whitelist(methods=["POST"])
def clear_conversations() -> dict:
	"""Delete every conversation the current user owns."""

	def run():
		require_access()
		names = frappe.get_all(service.CONVERSATION, filters={"user": frappe.session.user}, pluck="name")
		for name in names:
			service.delete_conversation(name)
		return {"ok": True, "deleted": len(names)}

	return _guard(run)


@frappe.whitelist(methods=["POST"])
def test_connection() -> dict:
	"""Administrators: send a one-line prompt with the saved provider settings."""
	frappe.only_for("System Manager")

	def run():
		settings = get_settings()
		if not settings:
			raise ChatbotError("not_configured", _("Chatbot Settings has not been created yet."))
		config = providers.load_config(settings)
		reply = providers.complete(
			config,
			"You are a connectivity check. Reply with the single word OK.",
			[{"role": "user", "content": "Connectivity check"}],
		)
		return {
			"ok": True,
			"provider": config.provider,
			"model": config.model,
			"latency_ms": reply.latency_ms,
			"reply": reply.text[:200],
		}

	return _guard(run)
