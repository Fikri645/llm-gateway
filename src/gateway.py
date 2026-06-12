"""Gateway orchestration — the single entry point every request flows through.

Phase 1: input → LLM → output. Phases 2-3 wrap this with guardrails (block /
redact at input and output) and Langfuse tracing without changing the call
sites. Returning a structured result keeps the API and UI stable as the
hardening layers land.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

from src import guardrails, llm

REFUSAL = ("I can't help with that request — it was flagged by the gateway's "
           "safety guardrails.")


@dataclass
class GatewayResult:
    answer: str
    blocked: bool = False
    block_reason: str = ""
    redacted_input: str | None = None
    provider: str = ""
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    verdicts: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def process(prompt: str) -> GatewayResult:
    """Input guardrails → LLM → output guardrails. Blocks short-circuit."""
    t0 = time.perf_counter()

    safe_prompt, in_v = guardrails.check_input(prompt)
    redacted = safe_prompt if in_v.redacted else None
    if in_v.blocked:
        return GatewayResult(
            answer=REFUSAL, blocked=True,
            block_reason="; ".join(in_v.reasons), redacted_input=redacted,
            provider="guardrails", latency_ms=round((time.perf_counter()-t0)*1000, 1),
            verdicts={"input": in_v.reasons})

    res = llm.complete(safe_prompt)
    safe_out, out_v = guardrails.check_output(safe_prompt, res.text)
    if out_v.blocked:
        return GatewayResult(
            answer=REFUSAL, blocked=True,
            block_reason="; ".join(out_v.reasons), redacted_input=redacted,
            provider=res.provider, cost_usd=res.cost_usd,
            latency_ms=round((time.perf_counter()-t0)*1000, 1),
            verdicts={"input": in_v.reasons, "output": out_v.reasons})

    return GatewayResult(
        answer=safe_out, redacted_input=redacted, provider=res.provider,
        cost_usd=res.cost_usd,
        latency_ms=round((time.perf_counter() - t0) * 1000, 1),
        verdicts={"input": in_v.reasons, "output": out_v.reasons})
