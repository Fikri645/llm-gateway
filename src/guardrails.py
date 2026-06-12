"""Input/output guardrails built on LLM Guard.

Two tiers so the gateway is both production-real and CI-friendly:

* **LITE (default):** deterministic scanners — `BanSubstrings` for
  prompt-injection phrases and banned/toxic terms, plus a `Regex` PII
  redactor. No model downloads → runs in CI and with no API key.
* **FULL (`GUARDRAILS_FULL=1`):** adds LLM Guard's model-based
  `PromptInjection` and `Toxicity` scanners for ML-grade detection.

Each check returns a `Verdict` (blocked + reasons + scores); the gateway
blocks on input/output violations and forwards the *redacted* prompt to the
model so PII never reaches the LLM.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from llm_guard import scan_output, scan_prompt
from llm_guard.input_scanners import BanSubstrings
from llm_guard.input_scanners.ban_substrings import MatchType

from src import config

INJECTION_PHRASES = [
    "ignore all previous", "ignore previous instructions", "disregard the",
    "forget everything", "you are now", "system:", "new directive",
    "no restrictions", "unfiltered ai", "pretend the previous",
    "act as dan", "you are dan", "reveal your system prompt",
]
TOXIC_TERMS = ["stupid", "idiot", "worthless", "i hate you", "kill",
               "violent threat", "hurt my"]
BANNED_PHRASES = ["illegal weapons", "self-harm", "hurt myself",
                  "build a bomb", "make a weapon"]

# PII patterns → redaction tag
PII_PATTERNS = {
    "EMAIL": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "PHONE": re.compile(r"(?:\+?\d[\d\-\s]{7,}\d)"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
}

FULL = os.environ.get("GUARDRAILS_FULL", "0") == "1"


@dataclass
class Verdict:
    blocked: bool = False
    reasons: list[str] = field(default_factory=list)
    redacted: bool = False
    scores: dict = field(default_factory=dict)


def _ban(substrings):
    return BanSubstrings(substrings=substrings, match_type=MatchType.STR,
                         case_sensitive=False, redact=False)


def _input_scanners():
    # one merged BanSubstrings — multiple BanSubstrings instances would share
    # the scanner name "BanSubstrings" and overwrite each other in the verdict
    # dict, silently dropping all but the last list.
    scanners = [_ban(INJECTION_PHRASES + BANNED_PHRASES + TOXIC_TERMS)]
    if FULL:
        from llm_guard.input_scanners import PromptInjection, Toxicity
        scanners += [PromptInjection(threshold=config.PROMPT_INJECTION_THRESHOLD),
                     Toxicity(threshold=config.TOXICITY_THRESHOLD)]
    return scanners


def redact_pii(text: str) -> tuple[str, list[str]]:
    found = []
    for tag, pat in PII_PATTERNS.items():
        if pat.search(text):
            found.append(tag)
            text = pat.sub(f"[REDACTED_{tag}]", text)
    return text, found


def check_input(prompt: str) -> tuple[str, Verdict]:
    """Redact PII, then run the input scanners. Returns (safe_prompt, verdict)."""
    v = Verdict()
    safe, pii = redact_pii(prompt)
    if pii:
        v.redacted = True
        v.reasons.append(f"redacted PII: {', '.join(pii)}")

    sanitized, valid, scores = scan_prompt(_input_scanners(), safe)
    v.scores = scores
    failed = [name for name, ok in valid.items() if not ok]
    if failed:
        v.blocked = True
        v.reasons.append("input blocked by: " + ", ".join(failed))
    return sanitized, v


def _output_scanners():
    # output scanners take (prompt, output); the *output* BanSubstrings has
    # that signature (the input one doesn't).
    from llm_guard.output_scanners import BanSubstrings as OutBan
    from llm_guard.output_scanners.ban_substrings import (
        MatchType as OutMatchType)
    scanners = [OutBan(substrings=TOXIC_TERMS, match_type=OutMatchType.STR,
                       case_sensitive=False)]
    if FULL:
        from llm_guard.output_scanners import Toxicity as OutToxicity
        scanners += [OutToxicity(threshold=config.TOXICITY_THRESHOLD)]
    return scanners


def check_output(prompt: str, output: str) -> tuple[str, Verdict]:
    """PII-leak redaction + toxicity scan on the model output."""
    v = Verdict()
    safe, pii = redact_pii(output)
    if pii:
        v.redacted = True
        v.reasons.append(f"output PII leak redacted: {', '.join(pii)}")

    sanitized, valid, scores = scan_output(_output_scanners(), prompt, safe)
    v.scores = scores
    failed = [name for name, ok in valid.items() if not ok]
    if failed:
        v.blocked = True
        v.reasons.append("output blocked by: " + ", ".join(failed))
    return sanitized, v
