"""Chatbot Conversation — one user's thread with the assistant.

Rows are created and read only through theme_myrmex.chatbot.api, which checks
ownership on every call. The DocType itself is readable by System Manager for
audit purposes; ordinary users have no Desk access to it.
"""

import frappe
from frappe.model.document import Document


class ChatbotConversation(Document):
	def on_trash(self):
		frappe.db.delete("Chatbot Message", {"conversation": self.name})
