# PatchGym Traces

TraceWeave can analyze a PatchGym run directory directly:

```bash
traceweave patchgym .patchgym/runs/latest
traceweave patchgym .patchgym/runs/latest --json
```

PatchGym writes `trace.jsonl` with one JSON object per event. TraceWeave treats
those events like any other local agent trace and reports:

- repeated action loops;
- tool churn;
- explicit error events;
- context drift;
- causal handoff edges;
- a conservative failure-risk score.

## Event Shape

PatchGym trace events include:

- `actor`: `patchgym` or `agent`;
- `tool`: subsystem such as `runner`, `agent_command`, `git`, or `validation`;
- `action`: event label such as `run`, `capture_patch`, or `task_result`;
- `status`: `ok` or `error`;
- `input` and `output`: structured details for the event.

TraceWeave treats `status: ok` as authoritative even if an output object has an
empty `error` field. This avoids false positives in normal PatchGym task-result
events.

