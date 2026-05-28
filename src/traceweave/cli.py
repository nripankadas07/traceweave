from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .core import analyze_events, load_jsonl, render_markdown


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="traceweave")
    sub = parser.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze", help="analyze a JSONL agent trace")
    analyze.add_argument("trace")
    analyze.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    args = parser.parse_args(argv)
    if args.command == "analyze":
        report = analyze_events(load_jsonl(args.trace))
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(render_markdown(report), end="")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
