"""Provider adapters.

Each adapter takes the same inputs (a system prompt and a user/assistant turn
list) and returns plain text plus token usage. The API key is read from the
encrypted Password field at call time and never leaves this module: it is not
logged, not returned, and not included in error messages.

Adding a provider means adding one function and one entry in ADAPTERS.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import frappe
import requests
from frappe import _
from frappe.utils import cint, flt

from theme_myrmex.chatbot.security import ChatbotError

DEFAULT_ENDPOINTS = {
	"OpenAI Compatible": "https://api.openai.com/v1/chat/completions",
	"Anthropic": "https://api.anthropic.com/v1/messages",
	"Azure OpenAI": "",
}

ANTHROPIC_VERSION = "2023-06-01"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


@dataclass
class ProviderConfig:
	provider: str
	endpoint: str
	api_key: str
	model: str
	temperature: float
	max_tokens: int
	timeout: int
	extra_headers: dict = field(default_factory=dict)


@dataclass
class ProviderReply:
	text: str
	prompt_tokens: int = 0
	completion_tokens: int = 0
	latency_ms: int = 0


def load_config(settings) -> ProviderConfig:
	"""Read provider settings, including the decrypted key, on the server."""
	provider = settings.get("ai_provider") or "OpenAI Compatible"
	endpoint = (settings.get("api_endpoint") or DEFAULT_ENDPOINTS.get(provider) or "").strip()

	api_key = ""
	if settings.get("api_key"):
		api_key = settings.get_password("api_key", raise_exception=False) or ""

	if not endpoint:
		raise ChatbotError("not_configured", _("The assistant has no API endpoint configured."), 503)
	if not settings.get("model"):
		raise ChatbotError("not_configured", _("The assistant has no model configured."), 503)
	if provider != "OpenAI Compatible" and not api_key:
		# OpenAI-compatible local servers (Ollama, vLLM) may run without a key.
		raise ChatbotError("not_configured", _("The assistant has no API key configured."), 503)

	return ProviderConfig(
		provider=provider,
		endpoint=endpoint,
		api_key=api_key,
		model=settings.get("model").strip(),
		temperature=max(0.0, min(2.0, flt(settings.get("temperature")))),
		max_tokens=max(64, min(16000, cint(settings.get("max_tokens")) or 800)),
		timeout=max(5, min(180, cint(settings.get("request_timeout")) or 30)),
	)


def complete(config: ProviderConfig, system_prompt: str, messages: list[dict]) -> ProviderReply:
	adapter = ADAPTERS.get(config.provider)
	if not adapter:
		raise ChatbotError("not_configured", _("Unknown AI provider: {0}").format(config.provider), 503)

	started = time.monotonic()
	reply = adapter(config, system_prompt, messages)
	reply.latency_ms = int((time.monotonic() - started) * 1000)

	if not reply.text.strip():
		raise ChatbotError("empty_reply", _("The assistant returned an empty answer. Try rephrasing."), 502)
	return reply


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


def _openai_compatible(config: ProviderConfig, system_prompt: str, messages: list[dict]) -> ProviderReply:
	headers = {"Content-Type": "application/json"}
	if config.api_key:
		headers["Authorization"] = f"Bearer {config.api_key}"
	return _chat_completions(config, headers, system_prompt, messages)


def _azure_openai(config: ProviderConfig, system_prompt: str, messages: list[dict]) -> ProviderReply:
	# Azure takes the key in its own header; the deployment and api-version are
	# part of the configured endpoint URL.
	headers = {"Content-Type": "application/json", "api-key": config.api_key}
	return _chat_completions(config, headers, system_prompt, messages)


def _chat_completions(config, headers, system_prompt, messages) -> ProviderReply:
	body = {
		"model": config.model,
		"messages": [{"role": "system", "content": system_prompt}, *messages],
		"temperature": config.temperature,
		"max_tokens": config.max_tokens,
	}
	data = _post(config, headers, body)

	try:
		text = data["choices"][0]["message"]["content"] or ""
	except (KeyError, IndexError, TypeError):
		_log_unexpected(config, data)
		raise ChatbotError("bad_reply", _("The AI provider sent a reply the assistant could not read."), 502)

	usage = data.get("usage") or {}
	return ProviderReply(
		text=text,
		prompt_tokens=cint(usage.get("prompt_tokens")),
		completion_tokens=cint(usage.get("completion_tokens")),
	)


def _anthropic(config: ProviderConfig, system_prompt: str, messages: list[dict]) -> ProviderReply:
	headers = {
		"Content-Type": "application/json",
		"x-api-key": config.api_key,
		"anthropic-version": ANTHROPIC_VERSION,
	}
	body = {
		"model": config.model,
		"system": system_prompt,
		"messages": messages,
		"max_tokens": config.max_tokens,
		"temperature": min(1.0, config.temperature),
	}
	data = _post(config, headers, body)

	blocks = data.get("content") if isinstance(data, dict) else None
	if not isinstance(blocks, list):
		_log_unexpected(config, data)
		raise ChatbotError("bad_reply", _("The AI provider sent a reply the assistant could not read."), 502)

	text = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
	usage = data.get("usage") or {}
	return ProviderReply(
		text=text,
		prompt_tokens=cint(usage.get("input_tokens")),
		completion_tokens=cint(usage.get("output_tokens")),
	)


ADAPTERS = {
	"OpenAI Compatible": _openai_compatible,
	"Azure OpenAI": _azure_openai,
	"Anthropic": _anthropic,
}


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


def _post(config: ProviderConfig, headers: dict, body: dict) -> dict:
	try:
		response = requests.post(
			config.endpoint,
			json=body,
			headers={**headers, **config.extra_headers},
			timeout=config.timeout,
			allow_redirects=False,
			stream=True,
		)
	except requests.Timeout:
		raise ChatbotError(
			"timeout", _("The assistant took too long to answer. Try again in a moment."), 504
		)
	except requests.RequestException as error:
		_log_transport_error(config, type(error).__name__)
		raise ChatbotError("unreachable", _("The assistant could not reach the AI provider."), 502)

	try:
		raw = response.raw.read(MAX_RESPONSE_BYTES + 1, decode_content=True)
	finally:
		response.close()

	if len(raw) > MAX_RESPONSE_BYTES:
		raise ChatbotError("bad_reply", _("The AI provider sent an unexpectedly large reply."), 502)

	if response.status_code in (401, 403):
		_log_http_error(config, response.status_code, raw)
		raise ChatbotError(
			"provider_auth",
			_("The AI provider rejected the assistant's credentials. Ask an administrator to check the API key."),
			502,
		)
	if response.status_code == 429:
		raise ChatbotError(
			"provider_busy", _("The AI provider is busy right now. Try again in a minute."), 503
		)
	if response.status_code >= 400:
		_log_http_error(config, response.status_code, raw)
		raise ChatbotError(
			"provider_error", _("The AI provider returned an error ({0}).").format(response.status_code), 502
		)

	try:
		return frappe.parse_json(raw.decode("utf-8")) or {}
	except Exception:
		_log_unexpected(config, raw[:500])
		raise ChatbotError("bad_reply", _("The AI provider sent a reply the assistant could not read."), 502)


def _redact(text: str, config: ProviderConfig) -> str:
	if config.api_key:
		text = text.replace(config.api_key, "***")
	return text


def _log_http_error(config: ProviderConfig, status: int, raw: bytes):
	body = raw[:1000].decode("utf-8", errors="replace")
	frappe.log_error(
		title=f"Myrmex Assistant: provider HTTP {status}",
		message=_redact(f"Provider: {config.provider}\nEndpoint: {config.endpoint}\n\n{body}", config),
	)


def _log_transport_error(config: ProviderConfig, error_name: str):
	frappe.log_error(
		title="Myrmex Assistant: provider unreachable",
		message=f"Provider: {config.provider}\nEndpoint: {config.endpoint}\nError: {error_name}",
	)


def _log_unexpected(config: ProviderConfig, payload):
	frappe.log_error(
		title="Myrmex Assistant: unexpected provider reply",
		message=_redact(f"Provider: {config.provider}\n\n{str(payload)[:1000]}", config),
	)
