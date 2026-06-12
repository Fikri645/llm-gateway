"""Central configuration for the LLM gateway."""
from __future__ import annotations

import logging
import os
from pathlib import Path

# Quiet LLM Guard's chatty structlog output (it logs every scan at info/debug).
try:
    import structlog
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING))
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
for _d in (DATA_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# LLM backend — provider-agnostic. With no key, the gateway uses a
# deterministic MOCK so the whole stack (guardrails, tracing, evals, CI) runs
# offline; set GEMINI_API_KEY to hit the real free-tier model.
# --------------------------------------------------------------------------- #
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "auto")   # auto | gemini | mock
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

# token pricing ($ / 1M tokens) for the cost estimator (Gemini 2.0 Flash)
PRICE_IN_PER_M = 0.10
PRICE_OUT_PER_M = 0.40

# --------------------------------------------------------------------------- #
# Guardrails thresholds
# --------------------------------------------------------------------------- #
TOXICITY_THRESHOLD = 0.5
PROMPT_INJECTION_THRESHOLD = 0.5
RELEVANCE_THRESHOLD = 0.3
BANNED_TOPICS = ["violence", "self-harm", "illegal weapons"]

# --------------------------------------------------------------------------- #
# Langfuse observability (self-host; gateway works fine if these are unset)
# --------------------------------------------------------------------------- #
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "http://localhost:3000")
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
