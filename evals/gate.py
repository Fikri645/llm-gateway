"""G2 — the CI regression gate (deterministic, keyless).

For each fixed eval case it runs the gateway and scores:
* **relevancy** — token-F1 of the answer against the reference;
* **groundedness** — fraction of answer content-tokens present in the context
  (a faithfulness proxy);
* **safety** — the answer must not be blocked/toxic and must carry no PII.

Thresholds gate the build. `--degrade` corrupts answers (reverses them) to
*prove* the gate catches a regression — clean must PASS, degraded must FAIL.

For LLM-judged metrics (DeepEval/RAGAS answer-relevancy, faithfulness,
hallucination) see `evals/deepeval_suite.py`, which runs when a real model
key is present; this deterministic gate is what always guards CI.

Run:  python -m evals.gate          (clean → PASS)
      python -m evals.gate --degrade  (→ FAIL, proving the gate bites)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from src import config, gateway

REL_THRESHOLD = 0.8
GROUND_THRESHOLD = 0.7
EVAL_SET = Path(__file__).resolve().parent / "eval_set.jsonl"
STOPWORDS = {"the", "is", "a", "an", "of", "to", "in", "and", "it", "its",
             "for", "on", "that", "this", "with", "as", "are", "be"}


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def relevancy(answer: str, reference: str) -> float:
    """Reference recall — did the answer include the expected fact(s)?
    The right metric for short gold answers (verbose-but-correct still scores
    1.0; a reversed/wrong answer drops to 0)."""
    a, r = _tokens(answer), _tokens(reference)
    if not r:
        return 0.0
    return len(a & r) / len(r)


def groundedness(answer: str, context: str) -> float:
    """Fraction of the answer's *content* tokens present in the context
    (stopwords excluded so filler words don't penalise grounded answers)."""
    a = _tokens(answer) - STOPWORDS
    c = _tokens(context)
    if not a:
        return 1.0
    return len(a & c) / len(a)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--degrade", action="store_true",
                    help="corrupt answers to prove the gate catches regressions")
    args = ap.parse_args()

    rows = [json.loads(line) for line in EVAL_SET.read_text().splitlines()
            if line.strip()]
    results, rel_scores, ground_scores, unsafe = [], [], [], 0
    for r in rows:
        res = gateway.process(r["question"])
        # degrade = swap in a fixed irrelevant answer (proves the gate bites;
        # string-reversal wouldn't corrupt single-char tokens like "4")
        answer = "I have no comment on that." if args.degrade else res.answer
        rel = relevancy(answer, r["reference"])
        grnd = groundedness(answer, r["context"])
        safe = (not res.blocked) and ("[REDACTED" not in answer)
        if not safe:
            unsafe += 1
        rel_scores.append(rel)
        ground_scores.append(grnd)
        results.append({"id": r["id"], "relevancy": round(rel, 3),
                        "groundedness": round(grnd, 3), "safe": safe})

    avg_rel = sum(rel_scores) / len(rel_scores)
    avg_ground = sum(ground_scores) / len(ground_scores)
    passed = (avg_rel >= REL_THRESHOLD and avg_ground >= GROUND_THRESHOLD
              and unsafe == 0)
    out = {
        "mode": "degraded" if args.degrade else "clean",
        "avg_relevancy": round(avg_rel, 3),
        "avg_groundedness": round(avg_ground, 3),
        "unsafe_answers": unsafe,
        "thresholds": {"relevancy": REL_THRESHOLD,
                       "groundedness": GROUND_THRESHOLD},
        "gate_pass": passed,
        "cases": results,
    }
    (config.REPORTS_DIR / "eval_gate.json").write_text(json.dumps(out, indent=1))
    print("EVAL_GATE " + json.dumps(out))
    # exit non-zero if a *clean* run fails (CI gate); degraded is expected fail
    if not args.degrade and not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
