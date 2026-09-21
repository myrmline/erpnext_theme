"""Chatbot Message — one turn of a conversation.

Only a reference to the page or document the user was on is stored
(context_ref), never the document data that was shared with the model.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class ChatbotMessage(Document):
	def validate(self):
		if self.role not in ("user", "assistant"):
			frappe.throw(_("Invalid message role: {0}").format(self.role))
