# Quality Notes

TraceWeave should remain deterministic and inspectable.

Current gates:

- unit tests for loop detection, stable signatures, and report rendering;
- CLI demo against `examples/trace.jsonl`;
- Python 3.9 and 3.13 CI;
- no API keys, network calls, or hosted telemetry in the default path.

New metrics should include a test fixture that makes both a positive and a
negative case easy to inspect.

