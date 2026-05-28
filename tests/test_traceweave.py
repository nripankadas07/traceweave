import unittest

from traceweave import analyze_events, event_signature, render_markdown


class TraceWeaveTests(unittest.TestCase):
    def test_detects_repeated_loop_and_errors(self):
        event = {"actor": "agent", "tool": "shell", "action": "run", "input": "pytest -q", "status": "error"}
        report = analyze_events([event, event, event, {"tool": "edit", "input": "fix parser", "output": "parser"}])
        self.assertGreater(report["repetition_ratio"], 0.0)
        self.assertGreaterEqual(report["error_events"], 3)
        self.assertTrue(report["loop_candidates"])
        self.assertIn("Risk score", render_markdown(report))

    def test_signature_is_stable_for_equivalent_events(self):
        left = {"tool": "search", "input": {"q": "parser bug"}, "status": "ok"}
        right = {"status": "ok", "input": {"q": "parser bug"}, "tool": "search"}
        self.assertEqual(event_signature(left), event_signature(right))


if __name__ == "__main__":
    unittest.main()
