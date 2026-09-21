"""Installation lifecycle hooks."""

import frappe

from theme_myrmex.api import clear_theme_cache
from theme_myrmex.presets import DEFAULTS

# (label, prompt, language, needs)
DEFAULT_SUGGESTIONS = [
	("Explain this page", "Explain what this page is for and what I can do here.", "en", ""),
	(
		"Help me find something",
		"Help me find something in the application. Ask me what I'm looking for.",
		"en",
		"",
	),
	(
		"Summarize this document",
		"Summarize this document: its status, key figures and anything that needs attention.",
		"en",
		"Document",
	),
	("Show my open tasks", "List my open assignments and suggest what to do first.", "en", ""),
	("Show my recent activity", "What have I changed recently here?", "en", "List"),
	(
		"Help with this module",
		"Give me a short guide to this module and its most common tasks.",
		"en",
		"",
	),
	("Expliquer cette page", "Explique à quoi sert cette page et ce que je peux y faire.", "fr", ""),
	(
		"Trouver quelque chose",
		"Aide-moi à trouver quelque chose dans l'application. Demande-moi ce que je cherche.",
		"fr",
		"",
	),
	(
		"Résumer ce document",
		"Résume ce document : son statut, les chiffres clés et ce qui demande une action.",
		"fr",
		"Document",
	),
	("Mes tâches ouvertes", "Liste mes affectations ouvertes et propose par quoi commencer.", "fr", ""),
	("Mon activité récente", "Qu'ai-je modifié récemment ici ?", "fr", "List"),
	(
		"Aide sur ce module",
		"Donne-moi un court guide de ce module et de ses tâches les plus courantes.",
		"fr",
		"",
	),
	("اشرح هذه الصفحة", "اشرح الغرض من هذه الصفحة وما يمكنني القيام به هنا.", "ar", ""),
	("ساعدني في إيجاد شيء", "ساعدني في إيجاد شيء داخل التطبيق. اسألني عمّا أبحث عنه.", "ar", ""),
	("لخّص هذا المستند", "لخّص هذا المستند: حالته وأهم الأرقام وما يحتاج إلى متابعة.", "ar", "Document"),
	("مهامي المفتوحة", "اعرض مهامي المفتوحة واقترح بماذا أبدأ.", "ar", ""),
	("نشاطي الأخير", "ما الذي عدّلته مؤخرًا هنا؟", "ar", "List"),
	("مساعدة في هذه الوحدة", "قدّم لي دليلًا مختصرًا لهذه الوحدة وأكثر مهامها شيوعًا.", "ar", ""),
]


def ensure_theme_settings():
	"""Create the Single doc with the default preset if it is still empty."""
	if not frappe.db.exists("DocType", "Theme Settings"):
		return

	doc = frappe.get_single("Theme Settings")
	changed = False
	for field, value in DEFAULTS.items():
		if doc.get(field) in (None, ""):
			doc.set(field, value)
			changed = True

	if changed:
		doc.flags.ignore_permissions = True
		doc.save()
		frappe.db.commit()


def _suggestion_rows():
	return [
		{"label": label, "prompt": prompt, "language": language, "needs": needs, "enabled": 1}
		for label, prompt, language, needs in DEFAULT_SUGGESTIONS
	]


@frappe.whitelist()
def default_chatbot_suggestions():
	"""The shipped suggestion rows, for the "Restore default suggestions" button."""
	frappe.only_for("System Manager")
	return _suggestion_rows()


def ensure_chatbot_settings():
	"""Seed Chatbot Settings once. Existing values are never overwritten.

	The assistant stays disabled until an administrator configures a provider.
	"""
	if not frappe.db.exists("DocType", "Chatbot Settings"):
		return

	doc = frappe.get_single("Chatbot Settings")
	if doc.get("bot_name"):
		# Already seeded, or configured by hand.
		return

	doc.bot_name = "Myrmex Assistant"
	doc.enabled = 0
	for row in _suggestion_rows():
		doc.append("suggestions", row)

	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.save()
	frappe.db.commit()


def after_install():
	ensure_theme_settings()
	ensure_chatbot_settings()
	clear_theme_cache()


def after_migrate():
	ensure_theme_settings()
	ensure_chatbot_settings()
	clear_theme_cache()


def after_app_install(app_name=None):
	"""Another app was installed; drop the cached payload so assets re-resolve."""
	clear_theme_cache()
