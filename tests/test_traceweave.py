import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from traceweave import analyze_events, event_signature, load_patchgym_run, render_markdown
from traceweave.cli import main


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

    def test_ok_event_with_empty_error_field_is_not_error(self):
        report = analyze_events(
            [
                {
                    "actor": "patchgym",
                    "tool": "grader",
                    "action": "task_result",
                    "status": "ok",
                    "output": {"solved": True, "error": ""},
                }
            ]
        )
        self.assertEqual(report["error_events"], 0)

    def test_patchgym_run_loader(self):
        with TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "trace.jsonl").write_text(
                '{"actor":"patchgym","tool":"runner","action":"run_start","status":"ok"}\n',
                encoding="utf-8",
            )
            self.assertEqual(len(load_patchgym_run(run_dir)), 1)
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["patchgym", str(run_dir), "--json"]), 0)


if __name__ == "__main__":
    unittest.main()
