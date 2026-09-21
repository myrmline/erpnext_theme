"""Unit tests for the pure helpers. They need no site, so they also run with
plain `python -m unittest theme_myrmex.chatbot.test_utils`."""

import unittest

from theme_myrmex.chatbot import utils


class TestUtils(unittest.TestCase):
	def test_clean_message(self):
		self.assertEqual(utils.clean_message("  hi\r\nthere\x00 ", 100), "hi\nthere")
		self.assertEqual(utils.clean_message("a\n\n\n\n\n\nb", 100), "a\n\n\nb")
		with self.assertRaises(utils.InvalidMessage) as ctx:
			utils.clean_message("   ", 100)
		self.assertEqual(ctx.exception.code, "empty")
		with self.assertRaises(utils.InvalidMessage) as ctx:
			utils.clean_message("x" * 11, 10)
		self.assertEqual(ctx.exception.code, "too_long")
		with self.assertRaises(utils.InvalidMessage):
			utils.clean_message(None, 10)

	def test_route_patterns(self):
		patterns = utils.parse_patterns("# comment\nForm/Sales Order/*\n\n/List/*/")
		self.assertEqual(patterns, ["form/sales order/*", "list/*"])
		self.assertTrue(utils.route_matches("Form/Sales Order/SO-0001", patterns))
		self.assertTrue(utils.route_matches("List/Customer/List", patterns))
		self.assertFalse(utils.route_matches("Workspaces/Home", patterns))
		self.assertTrue(utils.is_visible_on_route("Workspaces/Home", "Everywhere", patterns))
		self.assertFalse(utils.is_visible_on_route("Workspaces/Home", "Only on listed pages", patterns))
		self.assertFalse(
			utils.is_visible_on_route("List/ToDo", "Everywhere except listed pages", patterns)
		)

	def test_sanitize_route(self):
		self.assertEqual(utils.sanitize_route("Form/Customer/Acme, Inc."), ["Form", "Customer", "Acme, Inc."])
		self.assertEqual(utils.sanitize_route(["Form", "<script>", 5, "x"]), ["Form", "x"])
		self.assertEqual(utils.sanitize_route({"a": 1}), [])
		self.assertEqual(len(utils.sanitize_route(["a"] * 20)), 6)

	def test_language(self):
		self.assertEqual(utils.resolve_language("French", "en"), ("fr", "French"))
		self.assertEqual(utils.resolve_language("User language", "ar"), ("ar", "Arabic"))
		self.assertEqual(utils.resolve_language("User language", "de"), ("de", "de"))
		self.assertEqual(utils.resolve_language(None, None), ("en", "English"))
		self.assertTrue(utils.is_rtl("ar"))
		self.assertFalse(utils.is_rtl("fr"))

	def test_trim_history(self):
		history = [
			{"role": "assistant", "content": "welcome"},
			{"role": "user", "content": "a" * 10},
			{"role": "assistant", "content": "b" * 10},
			{"role": "user", "content": "c" * 10},
		]
		self.assertEqual([m["content"][0] for m in utils.trim_history(history, 10, 1000)], ["a", "b", "c"])
		self.assertEqual([m["content"][0] for m in utils.trim_history(history, 10, 15)], ["c"])
		self.assertEqual(utils.trim_history(history, 0, 1000), [])

	def test_merge_consecutive(self):
		merged = utils.merge_consecutive(
			[{"role": "user", "content": "a"}, {"role": "user", "content": "b"}, {"role": "assistant", "content": "c"}]
		)
		self.assertEqual(merged, [{"role": "user", "content": "a\n\nb"}, {"role": "assistant", "content": "c"}])

	def test_client_history_validation(self):
		clean = utils.validate_client_history(
			[
				{"role": "system", "content": "evil"},
				{"role": "user", "content": "x" * 50},
				{"role": "assistant", "content": 42},
				"junk",
			],
			max_length=10,
			max_messages=10,
		)
		self.assertEqual(len(clean), 1)
		self.assertEqual(clean[0]["role"], "user")
		self.assertLessEqual(len(clean[0]["content"]), 10)
		self.assertEqual(utils.validate_client_history("nope", 10, 10), [])

	def test_title(self):
		self.assertEqual(utils.make_title("\n\n  Where   is\tmy invoice?\nmore"), "Where is my invoice?")
		self.assertTrue(utils.make_title("x" * 100).endswith("…"))


if __name__ == "__main__":
	unittest.main()
