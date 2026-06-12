# Production LLM Gateway

A model-agnostic gateway that wraps any chat/RAG backend with the production
hardening layer real AI-platform roles ask for: **input/output guardrails**,
**observability** (tracing + cost/latency), and a **CI eval regression gate**.

The whole stack runs **with no API key** on a deterministic mock backend, so
guardrails, evals, and CI are fully reproducible. Set `GEMINI_API_KEY` to route
to the real Gemini Flash free tier instead.

> Built to close the Tier-3 gap from a 2026 Indonesian job-market scan (the Flip
> "AI Platform Engineer" JD: LangSmith/Braintrust evals, guardrails, content
> filtering, cost/latency monitoring). See `RESEARCH.md` and `PLAN.md`.

## What it does

```
request ─▶ input guardrails ─▶ LLM ─▶ output guardrails ─▶ response
              │ (block/redact)         │ (block leaks)        │
              └──────────── trace (JSONL + optional Langfuse) ─┘
```

- **Guardrails** (LLM Guard): prompt-injection detection, PII redaction
  (email / phone / credit-card), toxicity, banned topics. Two tiers: `LITE`
  (deterministic, keyless, runs in CI) and `FULL` (`GUARDRAILS_FULL=1`, adds
  model-based PromptInjection + Toxicity scanners).
- **Observability**: every request traced to local JSONL (always-on) plus
  optional self-hosted Langfuse. Fire-and-forget — a tracing outage never
  breaks a response.
- **Eval regression gate**: a deterministic reference-recall + groundedness +
  safety gate that runs in CI (keyless), plus a key-gated DeepEval/RAGAS
  LLM-as-judge layer on top.

## Measured results (all PASS — see `reports/results.md`)

| Gate | Result |
|:--|:--|
| **G1** guardrails | 9/9 attacks blocked, 4/4 PII redacted, **0 leaks**, 4/4 benign passed |
| **G2** eval gate | clean PASS (rel 1.0, ground 1.0); `--degrade` FAILS — proves the gate bites |
| **G3** observability | every request traced (JSONL + optional Langfuse), graceful degradation |
| **G4** cost/latency | `/metrics` p50/p99 + $/1k; per-response token cost |

## Quickstart (no API key needed)

```bash
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt

# 1. Guardrails red-team (G1)
python -m src.redteam_score

# 2. Eval regression gate (G2) — exits non-zero on a real regression
python -m evals.gate
python -m evals.gate --degrade      # watch it FAIL on purpose

# 3. Unit tests (keyless)
pytest tests/ -v

# 4. API server
uvicorn api.main:app --reload
#   POST /chat {"message": "..."}   GET /health   GET /metrics

# 5. Gradio demo with live guardrail badges
python app.py
```

To use the real model instead of the mock: `set GEMINI_API_KEY=...` (Windows)
before running. For model-based guardrails: `set GUARDRAILS_FULL=1`.
For Langfuse tracing: bring up `docker-compose.yml` and set the Langfuse keys
in `src/config.py` / env.

## Endpoints

| Method | Path | Purpose |
|:--|:--|:--|
| POST | `/chat` | guardrailed completion (input scan → LLM → output scan) |
| GET | `/health` | liveness + active provider |
| GET | `/metrics` | rolling p50/p99 latency + cost per 1k |

## Layout

```
src/        gateway.py · guardrails.py · llm.py · tracing.py · config.py · redteam_score.py
evals/      gate.py (deterministic) · deepeval_suite.py (LLM-judge) · eval_set.jsonl
api/        main.py (FastAPI)
app.py      Gradio demo
data/       redteam.jsonl (17 cases)
reports/    results.md (measured numbers)
```

## Stack

LLM Guard · Langfuse · DeepEval + RAGAS · FastAPI · Gradio · Gemini Flash
(free tier) / deterministic mock · GitHub Actions CI (flake8 + pytest + G1 + G2).
