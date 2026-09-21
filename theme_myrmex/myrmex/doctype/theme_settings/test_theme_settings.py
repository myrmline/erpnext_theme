import frappe
from frappe.tests.utils import FrappeTestCase

from theme_myrmex.api import build_payload, get_settings


class TestThemeSettings(FrappeTestCase):
	def test_short_hex_is_expanded(self):
		doc = frappe.get_single("Theme Settings")
		doc.primary_color = "#abc"
		doc.validate()
		self.assertEqual(doc.primary_color, "#AABBCC")

	def test_invalid_hex_is_rejected(self):
		doc = frappe.get_single("Theme Settings")
		doc.primary_color = "not-a-colour"
		with self.assertRaises(frappe.ValidationError):
			doc.validate()

	def test_sidebar_width_is_clamped(self):
		doc = frappe.get_single("Theme Settings")
		doc.sidebar_width = 9000
		doc.validate()
		self.assertLessEqual(doc.sidebar_width, 380)

	def test_payload_has_both_colour_schemes(self):
		payload = build_payload(get_settings())
		self.assertIn("--myrmex-primary", payload["vars"])
		self.assertIn("--myrmex-background", payload["dark_vars"])
		self.assertIn("--myrmex-card-radius", payload["shared_vars"])
		self.assertTrue(payload["shared_vars"]["--myrmex-card-radius"].endswith("px"))
