from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Union
import hashlib
import json
import math
import re


TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]+|[0-9]+")
ERROR_WORDS = ("error", "exception", "traceback", "failed", "timeout", "denied")


def load_jsonl(path: Union[str, Path]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{line_no}: trace event must be an object")
        events.append(item)
    return events


def load_patchgym_run(path: Union[str, Path]) -> List[Dict[str, Any]]:
    run_dir = Path(path)
    trace = run_dir / "trace.jsonl"
    if not trace.exists():
        raise FileNotFoundError(f"PatchGym trace not found: {trace}")
    return load_jsonl(trace)


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _tokens(value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, str):
        value = _stable_json(value)
    return [token.lower() for token in TOKEN_RE.findall(value)]


def event_signature(event: Mapping[str, Any]) -> str:
    actor = str(event.get("actor", "agent")).lower()
    tool = str(event.get("tool", event.get("type", "unknown"))).lower()
    action = str(event.get("action", event.get("name", "step"))).lower()
    status = str(event.get("status", "ok")).lower()
    input_digest = hashlib.sha256(" ".join(_tokens(event.get("input", ""))).encode()).hexdigest()[:10]
    return f"{actor}:{tool}:{action}:{status}:{input_digest}"


def _is_error(event: Mapping[str, Any]) -> bool:
    status = str(event.get("status", "")).lower()
    explicit_error = str(event.get("error", "")).strip()
    if status in {"ok", "pass", "passed", "success", "succeeded"}:
        return bool(explicit_error)
    if status in {"error", "failed", "fail", "timeout"}:
        return True
    text = " ".join(
        str(event.get(key, "")).lower()
        for key in ("error", "output", "message", "stderr")
    )
    return any(word in text for word in ERROR_WORDS)


def detect_loops(signatures: Sequence[str], max_period: int = 6) -> List[Dict[str, Any]]:
    loops: Dict[tuple[int, int, tuple[str, ...]], Dict[str, Any]] = {}
    n = len(signatures)
    for start in range(n):
        for period in range(1, min(max_period, (n - start) // 2) + 1):
            unit = tuple(signatures[start:start + period])
            repeats = 1
            cursor = start + period
            while cursor + period <= n and tuple(signatures[cursor:cursor + period]) == unit:
                repeats += 1
                cursor += period
            if repeats >= 2:
                key = (start, period, unit)
                loops[key] = {
                    "start": start,
                    "period": period,
                    "repeats": repeats,
                    "span": period * repeats,
                    "signature_preview": list(unit[:3]),
                    "score": period * repeats,
                }
    ranked = sorted(loops.values(), key=lambda item: (-item["score"], item["start"]))
    return ranked[:10]


def context_drift(events: Sequence[Mapping[str, Any]]) -> float:
    if len(events) < 2:
        return 0.0
    distances: List[float] = []
    for left, right in zip(events, events[1:]):
        left_tokens = set(_tokens(left.get("input", "")) + _tokens(left.get("output", "")))
        right_tokens = set(_tokens(right.get("input", "")) + _tokens(right.get("output", "")))
        if not left_tokens and not right_tokens:
            continue
        union = left_tokens | right_tokens
        distances.append(1.0 - (len(left_tokens & right_tokens) / max(1, len(union))))
    return round(sum(distances) / len(distances), 4) if distances else 0.0


def causal_edges(events: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    overlaps: defaultdict[tuple[str, str], List[float]] = defaultdict(list)
    for left, right in zip(events, events[1:]):
        source = f"{left.get('actor', 'agent')}:{left.get('tool', left.get('type', 'unknown'))}"
        target = f"{right.get('actor', 'agent')}:{right.get('tool', right.get('type', 'unknown'))}"
        counts[(source, target)] += 1
        left_tokens = set(_tokens(left.get("output", "")) + _tokens(left.get("input", "")))
        right_tokens = set(_tokens(right.get("input", "")))
        if left_tokens or right_tokens:
            overlaps[(source, target)].append(len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens)))
    edges = []
    for (source, target), count in counts.items():
        edge_overlaps = overlaps.get((source, target), [0.0])
        edges.append(
            {
                "source": source,
                "target": target,
                "count": count,
                "mean_token_overlap": round(sum(edge_overlaps) / len(edge_overlaps), 4),
            }
        )
    return sorted(edges, key=lambda edge: (-edge["count"], edge["source"], edge["target"]))


def analyze_events(events: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    materialized = [dict(event) for event in events]
    signatures = [event_signature(event) for event in materialized]
    loops = detect_loops(signatures)
    errors = sum(1 for event in materialized if _is_error(event))
    total = len(materialized)
    switches = sum(
        1
        for left, right in zip(materialized, materialized[1:])
        if left.get("tool", left.get("type")) != right.get("tool", right.get("type"))
    )
    unique = len(set(signatures))
    repetition_ratio = 1.0 - (unique / total) if total else 0.0
    churn = switches / max(1, total - 1)
    drift = context_drift(materialized)
    loop_pressure = min(1.0, sum(loop["span"] for loop in loops[:3]) / max(1, total * 2))
    error_rate = errors / max(1, total)
    risk = 1.0 - math.prod([1.0 - loop_pressure, 1.0 - error_rate, 1.0 - drift * 0.35, 1.0 - churn * 0.15])
    return {
        "total_events": total,
        "unique_signatures": unique,
        "repetition_ratio": round(repetition_ratio, 4),
        "tool_churn": round(churn, 4),
        "error_events": errors,
        "error_rate": round(error_rate, 4),
        "context_drift": drift,
        "loop_candidates": loops,
        "causal_edges": causal_edges(materialized),
        "risk_score": round(min(1.0, risk), 4),
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# TraceWeave Report",
        "",
        f"- Events: {report['total_events']}",
        f"- Unique action signatures: {report['unique_signatures']}",
        f"- Repetition ratio: {report['repetition_ratio']}",
        f"- Tool churn: {report['tool_churn']}",
        f"- Error rate: {report['error_rate']}",
        f"- Context drift: {report['context_drift']}",
        f"- Risk score: {report['risk_score']}",
        "",
        "## Loop Candidates",
    ]
    loops = report.get("loop_candidates", [])
    if not loops:
        lines.append("No consecutive repeated action loops detected.")
    for loop in loops:
        lines.append(
            f"- start={loop['start']} period={loop['period']} repeats={loop['repeats']} span={loop['span']}"
        )
    lines.extend(["", "## Causal Edges"])
    for edge in report.get("causal_edges", [])[:20]:
        lines.append(
            f"- {edge['source']} -> {edge['target']}: {edge['count']} handoff(s), overlap={edge['mean_token_overlap']}"
        )
    return "\n".join(lines) + "\n"
