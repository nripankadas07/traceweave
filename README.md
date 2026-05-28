# TraceWeave

TraceWeave is a local-first forensics engine for AI-agent
trajectories. It reads JSONL traces, builds a compact causal
graph, detects repeated action loops, estimates context drift,
and emits an auditable risk report.

The design goal is deliberately narrow: give researchers and
engineers a deterministic way to answer, "Why did this agent
waste steps or fail?" without uploading traces to a hosted
observability product.

## Why It Exists

High-star agent frameworks optimize orchestration. TraceWeave
studies the failure residue those frameworks leave behind:
repeated tool calls, unstable context, error bursts, and
brittle action handoffs. It is meant to pair with coding-agent
benchmark harnesses such as PatchGym.

## Install

```bash
git clone https://github.com/nripankadas07/traceweave
cd traceweave
python -m pip install -e .
```

## Quick Start

```bash
traceweave analyze examples/trace.jsonl
traceweave analyze examples/trace.jsonl --json
traceweave patchgym .patchgym/runs/latest --json
```

A trace is newline-delimited JSON:

```json
{"actor":"agent","tool":"shell","action":"run","input":"pytest -q","status":"error","output":"1 failed"}
{"actor":"agent","tool":"edit","action":"patch","input":"fix parser","status":"ok","output":"changed parser.py"}
```

## What It Measures

- repeated action signatures and consecutive loop periods
- tool churn and error bursts
- context drift between neighboring events
- causal handoff edges between actors, tools, and actions
- a conservative risk score for failed or wasteful runs

## Non-goals

TraceWeave is not a hosted dashboard, not a model judge, and
not a replacement for full OpenTelemetry pipelines. It is a
small deterministic lens for local traces.

## PatchGym

See [PatchGym traces](docs/patchgym-traces.md) for the direct integration with
PatchGym run directories.

## Development

```bash
python -m unittest discover -s tests -v
```
