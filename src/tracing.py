"""Observability — every request is traced, two sinks, both fire-and-forget.

* **Local JSONL** (`reports/traces.jsonl`): always written — a dependency-free
  audit trail of prompt (redacted), output, provider, tokens, cost, latency,
  guardrail verdicts, and block status. This is the always-on observability.
* **Langfuse** (optional): if `LANGFUSE_PUBLIC_KEY`/`SECRET_KEY` are set, the
  same record is shipped to a self-hosted Langfuse for the hosted trace UI +
  cost/latency dashboards (see `docker-compose.yml`).

A tracing failure (disk, network, Langfuse down) must never break a response —
everything is wrapped and swallowed.
"""
from __future__ import annotations

import json
import time

from src import config

TRACE_LOG = config.REPORTS_DIR / "traces.jsonl"
_lf = None
_lf_tried = False


def _langfuse():
    global _lf, _lf_tried
    if _lf_tried:
        return _lf
    _lf_tried = True
    if not (config.LANGFUSE_PUBLIC_KEY and config.LANGFUSE_SECRET_KEY):
        return None
    try:
        from langfuse import Langfuse
        _lf = Langfuse(public_key=config.LANGFUSE_PUBLIC_KEY,
                       secret_key=config.LANGFUSE_SECRET_KEY,
                       host=config.LANGFUSE_HOST)
    except Exception as e:                       # never block on tracing
        print(f"[tracing] langfuse disabled: {e}")
        _lf = None
    return _lf


def trace(prompt: str, result) -> None:
    record = {
        "ts": time.time(),
        "prompt": (result.redacted_input or prompt)[:500],
        "answer": (result.answer or "")[:500],
        "blocked": result.blocked,
        "block_reason": result.block_reason,
        "provider": result.provider,
        "cost_usd": result.cost_usd,
        "latency_ms": result.latency_ms,
        "verdicts": result.verdicts,
    }
    try:
        with open(TRACE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

    lf = _langfuse()
    if lf is not None:
        try:
            lf.trace(name="gateway-chat",
                     input=record["prompt"], output=record["answer"],
                     metadata={k: record[k] for k in
                               ("blocked", "provider", "cost_usd",
                                "latency_ms", "verdicts")})
        except Exception:
            pass
