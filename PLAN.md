# Project Plan — Production LLM Gateway (guardrails + evals + observability)

> Status: **EXECUTING.** Stack rationale in [RESEARCH.md](RESEARCH.md).
> Pitch: *"A model-agnostic LLM gateway that wraps any chat/RAG backend with
> input/output guardrails (LLM Guard), full tracing + cost/latency
> (Langfuse), and a DeepEval/RAGAS regression gate in CI — the production
> safety + evaluation layer from the Flip AI-Platform JD, at Rp 0."*
> Closes the Tier-3 **LLM eval/observability + guardrails** gaps.

## Phases

### Phase 1 — Scaffold + model-agnostic adapter + mock (½ day)
Repo, venv 3.11, `src/config.py`, `src/llm.py` (provider-agnostic adapter:
Gemini Flash + a deterministic **mock backend** so everything runs with no
key), FastAPI `/chat` skeleton, smoke test on the mock.

### Phase 2 — Guardrails (LLM Guard) (~1 day)
`src/guardrails.py`: input scanners (PromptInjection, Anonymize/PII, Toxicity,
BanTopics) + output scanners (Deanonymize, Sensitive/PII-leak, Toxicity,
Relevance). Each returns a verdict + reason; the gateway blocks or redacts.
**G1 red-team set** (`data/redteam.jsonl`: injection, PII, toxic) + a scorer
script measuring block/leak rate.

### Phase 3 — Observability (Langfuse self-host) (~1 day)
docker-compose Langfuse (+ Postgres). Wrap every `/chat` call in a Langfuse
trace: prompt, output, tokens, **cost**, latency, guardrail verdicts.
Fire-and-forget so a Langfuse outage never breaks serving (**G3**). A
`/metrics` endpoint + the Langfuse dashboard show $/1k + p50/p99 (**G4**).

### Phase 4 — Eval regression gate (DeepEval + RAGAS) (~1 day)
`evals/` fixed Q&A set; DeepEval metrics (answer-relevancy, faithfulness,
toxicity) + RAGAS; thresholds enforced. A deliberately worsened prompt must
**fail** the gate (**G2**). Wired into CI (mock-judge for determinism, or
Gemini-judge when a key is present).

### Phase 5 — Serving UI + tests + CI (~1 day)
Gradio chat UI showing the answer + guardrail badges + live cost/latency.
pytest (guardrail verdicts on fixtures, adapter, cost math — no key needed),
flake8, GitHub Actions (lint + tests + the eval gate on the mock).

### Phase 6 — Ship
GitHub + CI · wiki ingest + gap analysis (Tier-3 eval/guardrails closed) ·
Career Profile + MOC · portfolio card · GitHub profile.

## Repo layout
```
llm-gateway/
├── RESEARCH.md · PLAN.md · README.md · docker-compose.yml (langfuse+pg)
├── src/
│   ├── config.py · llm.py (adapter+mock) · guardrails.py
│   ├── gateway.py (orchestration) · tracing.py (langfuse) · cost.py
│   └── redteam_score.py
├── api/main.py (FastAPI /chat /metrics) · app.py (Gradio)
├── evals/ (deepeval + ragas suite, fixed sets)
├── data/redteam.jsonl · tests/ · .github/workflows/ci.yml · reports/
```

## Definition of Done
- [ ] `/chat` with input+output guardrails, blocking/redacting with reasons
- [ ] G1-G4 measured in `reports/results.md`
- [ ] Langfuse tracing every call (cost+latency+verdicts); graceful when down
- [ ] DeepEval/RAGAS gate in CI; a worsened prompt fails it
- [ ] tests + flake8 + CI green; runs with **no API key** (mock)
- [ ] wiki + portfolio + GitHub profile updated
```
