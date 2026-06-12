"""Gateway orchestration — the single entry point every request flows through.

Phase 1: input → LLM → output. Phases 2-3 wrap this with guardrails (block /
redact at input and output) and Langfuse tracing without changing the call
sites. Returning a structured result keeps the API and UI stable as the
hardening layers land.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from src import llm


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
    """Run one prompt through the gateway (guardrails wired in Phase 2)."""
    res = llm.complete(prompt)
    return GatewayResult(
        answer=res.text,
        provider=res.provider,
        cost_usd=res.cost_usd,
        latency_ms=round(res.latency_ms, 1),
    )
