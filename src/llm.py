"""Provider-agnostic LLM adapter.

`complete(prompt)` returns a `LLMResult` (text + token counts + latency). With
no API key it falls back to a **deterministic mock** so the gateway, tests,
evals, and CI all run offline. Set `GEMINI_API_KEY` to use the real free-tier
Gemini Flash model.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from src import config


@dataclass
class LLMResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    provider: str

    @property
    def cost_usd(self) -> float:
        return round(
            self.prompt_tokens / 1e6 * config.PRICE_IN_PER_M
            + self.completion_tokens / 1e6 * config.PRICE_OUT_PER_M, 6)


def _approx_tokens(s: str) -> int:
    # ~4 chars/token heuristic; good enough for the mock + cost demo
    return max(1, len(s) // 4)


def _mock_complete(prompt: str) -> LLMResult:
    """Deterministic, knowledge-light echo-style answer for offline runs."""
    t0 = time.perf_counter()
    # a canned-but-plausible answer; deterministic for the same prompt
    p = prompt.strip().lower()
    if "capital of france" in p:
        ans = "The capital of France is Paris."
    elif "2+2" in p or "2 + 2" in p:
        ans = "2 + 2 = 4."
    else:
        ans = ("[mock] I can answer that based on the provided context. "
               "(Set GEMINI_API_KEY for a real model response.)")
    return LLMResult(ans, _approx_tokens(prompt), _approx_tokens(ans),
                     (time.perf_counter() - t0) * 1000, "mock")


def _gemini_complete(prompt: str) -> LLMResult:
    import google.generativeai as genai

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(config.GEMINI_MODEL)
    t0 = time.perf_counter()
    resp = model.generate_content(prompt)
    latency = (time.perf_counter() - t0) * 1000
    usage = getattr(resp, "usage_metadata", None)
    pt = getattr(usage, "prompt_token_count", _approx_tokens(prompt))
    ct = getattr(usage, "candidates_token_count", _approx_tokens(resp.text))
    return LLMResult(resp.text, pt, ct, latency, "gemini")


def complete(prompt: str) -> LLMResult:
    provider = config.LLM_PROVIDER
    use_gemini = (provider == "gemini"
                  or (provider == "auto" and config.GEMINI_API_KEY))
    if use_gemini:
        try:
            return _gemini_complete(prompt)
        except Exception as e:                 # never hard-fail serving
            print(f"[llm] gemini failed ({e}); falling back to mock")
    return _mock_complete(prompt)
