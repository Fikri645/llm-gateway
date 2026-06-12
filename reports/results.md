# Results — Production LLM Gateway (measured 2026-06-12)

A model-agnostic gateway wrapping any chat/RAG backend with guardrails,
tracing, and a CI eval gate. Runs keyless on a deterministic mock; set
`GEMINI_API_KEY` for the real free-tier model.

## G1 — Guardrails efficacy (red-team set, 17 cases)
- **Attacks blocked: 9/9** (prompt-injection, toxicity, banned topics)
- **PII redacted: 4/4** (email, phone, credit-card) — redacted *before* the model
- **PII leaks in output: 0**
- **Benign passed: 4/4** (false-block rate 0%)
- **G1 PASS.** Deterministic LITE scanners (LLM Guard `BanSubstrings` + regex
  PII) run keyless in CI; `GUARDRAILS_FULL=1` adds model-based PromptInjection
  + Toxicity.

## G2 — Eval regression gate (deterministic, CI)
- Clean run: relevancy **1.0**, groundedness **1.0** → **PASS** (exit 0).
- `--degrade` run: relevancy **0.0** → **FAIL** — proving the gate catches a
  regression. LLM-judged DeepEval (AnswerRelevancy + Faithfulness via a Gemini
  judge) layers on top, key-gated (skips in CI).

## G3 — Observability (graceful)
Every request is traced to local JSONL (always-on, dependency-free) **and**
optional self-hosted Langfuse (fire-and-forget — a tracing outage never breaks
a response). Verified: 3 requests → 3 trace records with cost, latency,
verdicts.

## G4 — Cost / latency
`/metrics` exposes rolling p50/p99 latency and cost per 1k requests; each
response carries its own token cost + latency. (Mock backend ~sub-ms; real
Gemini latencies flow through unchanged.)

## War stories
1. Three `BanSubstrings` instances collapsed in the verdict dict (shared
   scanner name) → only the last list applied (3/9 blocked); merged to one.
2. Input vs output scanner signatures differ (`scan(prompt)` vs
   `scan(prompt, output)`) — used the output `BanSubstrings` for output.
3. PII regex ordering: a 13-digit phone matched the credit-card pattern;
   tightened the card pattern to 4×4 groups and ordered it first.
4. gradio pulled `huggingface-hub` 1.x, breaking llm-guard's transformers
   (needs <1.0) — pinned `huggingface-hub<1.0`.
