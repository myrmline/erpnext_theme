"""Pure helpers for the chatbot.

Nothing in this module imports frappe, so it can be unit-tested without a site
and reused from any layer. Everything that touches the database, the cache or
the session lives in the sibling modules.
"""

from __future__ import annotations

import fnmatch
import re
import unicodedata

# Language setting label -> (ISO code, English name used in the system prompt).
LANGUAGES = {
	"English": ("en", "English"),
	"French": ("fr", "French"),
	"Arabic": ("ar", "Arabic"),
}

RTL_LANGUAGES = {"ar", "fa", "he", "ur", "ps"}

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_EXCESS_BLANK_LINES = re.compile(r"\n{4,}")
# Document names can hold almost anything ("Acme, Inc.", "#42"), and a segment
# is only ever used after a DocType existence and permission check, so reject
# just control characters, markup and backslashes.
_ROUTE_SEGMENT = re.compile(r"^[^\x00-\x1f\x7f<>\\]{1,140}$")


class InvalidMessage(ValueError):
	"""Raised when a user message cannot be accepted. `code` is machine-readable."""

	def __init__(self, code: str):
		super().__init__(code)
		self.code = code


def clean_message(text, max_length: int) -> str:
	"""Normalise a user message and enforce the length limit.

	Control characters are dropped (newlines and tabs are kept), line endings are
	unified, runs of blank lines are collapsed, and the result is stripped.
	"""
	if not isinstance(text, str):
		raise InvalidMessage("empty")

	text = unicodedata.normalize("NFC", text)
	text = text.replace("\r\n", "\n").replace("\r", "\n")
	text = _CONTROL_CHARS.sub("", text)
	text = _EXCESS_BLANK_LINES.sub("\n\n\n", text).strip()

	if not text:
		raise InvalidMessage("empty")
	if len(text) > max_length:
		raise InvalidMessage("too_long")
	return text


def truncate(value, limit: int) -> str:
	"""Stringify and shorten a value, marking the cut with an ellipsis."""
	text = "" if value is None else str(value)
	text = _CONTROL_CHARS.sub("", text).strip()
	if len(text) <= limit:
		return text
	return text[: max(0, limit - 1)].rstrip() + "…"


def parse_patterns(text) -> list[str]:
	"""One route pattern per line; blank lines and # comments are ignored."""
	patterns = []
	for line in (text or "").splitlines():
		line = line.strip()
		if line and not line.startswith("#"):
			patterns.append(line.strip("/").lower())
	return patterns


def route_matches(route: str, patterns: list[str]) -> bool:
	"""Glob-match a route such as "Form/Sales Order/SO-0001" against patterns.

	Matching is case-insensitive and `*` crosses segment boundaries, so
	"form/sales order*" covers every Sales Order form.
	"""
	route = (route or "").strip("/").lower()
	return any(fnmatch.fnmatchcase(route, pattern) for pattern in patterns)


def is_visible_on_route(route: str, mode: str, patterns: list[str]) -> bool:
	"""Apply the "Show on pages" setting to one route."""
	if mode == "Only on listed pages":
		return route_matches(route, patterns)
	if mode == "Everywhere except listed pages":
		return not route_matches(route, patterns)
	return True


def sanitize_route(route) -> list[str]:
	"""Accept a Desk route from the browser, keep only plausible segments."""
	if isinstance(route, str):
		route = route.split("/")
	if not isinstance(route, (list, tuple)):
		return []

	clean = []
	for segment in list(route)[:6]:
		if not isinstance(segment, str):
			continue
		segment = segment.strip()
		if segment and _ROUTE_SEGMENT.match(segment):
			clean.append(segment)
	return clean


def resolve_language(setting: str | None, user_lang: str | None) -> tuple[str, str]:
	"""Return (code, English name) for the language replies should use."""
	if setting in LANGUAGES:
		return LANGUAGES[setting]

	code = (user_lang or "en").split("-")[0].lower()
	for lang_code, name in LANGUAGES.values():
		if lang_code == code:
			return lang_code, name
	# Any other Frappe language: pass the code through and let the model cope.
	return code, code


def is_rtl(code: str | None) -> bool:
	return (code or "").split("-")[0].lower() in RTL_LANGUAGES


def trim_history(messages: list[dict], max_messages: int, max_chars: int) -> list[dict]:
	"""Keep the most recent turns that fit both limits.

	The list is trimmed from the oldest end, and a leading assistant turn is
	dropped so the sequence sent to the provider always opens with the user.
	"""
	kept: list[dict] = []
	total = 0
	for message in reversed(messages[-max_messages:] if max_messages > 0 else []):
		size = len(message.get("content") or "")
		if kept and total + size > max_chars:
			break
		kept.append(message)
		total += size

	kept.reverse()
	while kept and kept[0].get("role") != "user":
		kept.pop(0)
	return kept


def merge_consecutive(messages: list[dict]) -> list[dict]:
	"""Merge back-to-back turns from the same role.

	Some providers reject two user turns in a row, which happens when an earlier
	request failed and no assistant reply was stored.
	"""
	merged: list[dict] = []
	for message in messages:
		if merged and merged[-1]["role"] == message["role"]:
			merged[-1] = {
				"role": message["role"],
				"content": merged[-1]["content"] + "\n\n" + message["content"],
			}
		else:
			merged.append({"role": message["role"], "content": message["content"]})
	return merged


def make_title(message: str, limit: int = 60) -> str:
	"""A conversation title from its first message."""
	first_line = next((line for line in message.splitlines() if line.strip()), message)
	return truncate(" ".join(first_line.split()), limit)


def validate_client_history(history, max_length: int, max_messages: int) -> list[dict]:
	"""Validate history the browser sends when server-side history is off.

	Only user/assistant roles are accepted and every entry is length-checked, so
	the browser cannot smuggle a system turn into the request.
	"""
	if not isinstance(history, list):
		return []

	clean = []
	for entry in history[-max_messages:]:
		if not isinstance(entry, dict):
			continue
		role = entry.get("role")
		content = entry.get("content")
		if role not in ("user", "assistant") or not isinstance(content, str):
			continue
		content = truncate(content, max_length * 2 if role == "assistant" else max_length)
		if content:
			clean.append({"role": role, "content": content})
	return clean
