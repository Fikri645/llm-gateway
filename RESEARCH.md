# Production LLM Gateway — 2026 Hardening Stack Research

> Compiled 2026-06-12. Driven by [[Portfolio Gap Analysis - Job Market 2026]]:
> the remaining Tier-3 gaps are **LLM eval/observability + guardrails** — the
> exact shape of the **Flip "AI Platform Engineer" JD** (LangSmith/Braintrust
> evals, guardrails, content filtering, cost/latency/error monitoring). Fikri
> has RAG + RAGAS already; this adds the *production safety + evaluation +
> observability* layer that turns "an LLM demo" into "an LLM platform".
> Budget: **free / self-host**.

---

## 1. The thesis

A portfolio full of LLM *demos* doesn't prove you can run LLMs *in production*.
The Flip JD asks for: guardrails & content filtering, evaluation frameworks +
feedback loops, and instrumentation (cost, latency, error rates). So this
project is a **model-agnostic LLM gateway** every app would call — wrapping any
chat/RAG backend with safety, tracing, and a CI eval gate.

## 2. Stack decisions

| Concern | Choice | Why (2026) |
|:--|:--|:--|
| **Guardrails** | **LLM Guard** (Protect AI) | Production-grade input+output scanners out of the box — prompt-injection, PII anonymize/redact, toxicity, ban-topics, no-refusal, relevance. Best broad coverage for a real gateway ([LLM Guard vs NeMo vs Guardrails AI](https://dev.to/agdex_ai/best-ai-agent-security-guardrails-tools-in-2026-llm-guard-vs-nemo-vs-guardrails-ai-5e5d)). |
| **Observability** | **Langfuse** (self-host, Docker) | Open-source (MIT), self-hostable; traces every step + **token cost + latency** + scores. Battle-tested for production ([2026 observability roundup](https://www.confident-ai.com/knowledge-base/compare/10-llm-observability-tools-to-evaluate-and-monitor-ai-2026)). |
| **Eval gate (CI)** | **DeepEval** ("Pytest for LLMs") + **RAGAS** | Unit-test-style LLM eval — answer relevancy, faithfulness, hallucination, toxicity — runnable in CI as a **regression gate**; free forever ([eval landscape](https://www.confident-ai.com/knowledge-base/compare/best-ai-evaluation-tools-for-prompt-experimentation-2026)). RAGAS for the RAG-specific metrics Fikri already knows. |
| **Prompt A/B** | **promptfoo** (optional) | YAML-driven prompt/regression comparison; lightweight. |
| **LLM backend** | **Gemini Flash** (free tier) — model-agnostic adapter | Free, fast; the gateway is provider-agnostic (adapter pattern) so OpenAI/Claude/Groq drop in. |
| **Serving** | FastAPI `/chat` + a small UI | Consistent with the portfolio; Langfuse traces wrap each call. |

**Considered, out of scope (documented):** NeMo Guardrails (Colang dialogue
policies — heavier than a stateless gateway needs); LangSmith/Braintrust (paid
SaaS — Langfuse is the OSS equivalent named in the JD's spirit); a **Go**
sidecar (the JD's "Go and Python" — noted as a future hardening, Python ships
first).

## 3. Architecture

```
client ──► FastAPI /chat
              │  1. INPUT guardrails (LLM Guard): prompt-injection, PII
              │     anonymize, toxicity, ban-topics  → block/redact + reason
              ▼
          LLM adapter (Gemini Flash; provider-agnostic)
              │  2. OUTPUT guardrails: PII leak, toxicity, relevance, refusal
              ▼
          response + guardrail verdicts + cost + latency
              │
              └──► Langfuse trace (prompt, output, tokens, $, ms, scores)

CI:  DeepEval + RAGAS suite over a fixed eval set → regression gate
     (PR fails if faithfulness / relevancy / toxicity cross thresholds)
```

## 4. Pre-Registered Targets

- **G1 — guardrails efficacy:** on a labeled red-team set (prompt-injection +
  PII + toxic prompts), measure **block/redact rate** and **leak rate**;
  target ≥90% attacks blocked, 0 PII leaks in output.
- **G2 — eval regression gate:** DeepEval/RAGAS metrics (answer-relevancy,
  faithfulness, toxicity) on a fixed Q&A set, with thresholds enforced in CI —
  a deliberately worsened prompt must **fail the gate**.
- **G3 — full observability:** every request produces a Langfuse trace with
  token cost, latency, and guardrail verdicts; a dashboard shows $/1k requests
  and p50/p99.
- **G4 — measured cost/latency:** end-to-end p50/p99 and cost per 1k requests,
  with the guardrail overhead isolated.

## 5. Risks

| Risk | Mitigation |
|:--|:--|
| LLM Guard pulls heavy ML models (toxicity, PII transformers) | pin a lean scanner set; first run downloads models once; CI uses mocked LLM + the deterministic scanners |
| Needs a Gemini API key (Fikri has one) | adapter pattern + a deterministic mock backend so the framework, tests, and CI run with **no key**; real calls optional |
| Langfuse self-host = Postgres + server containers | docker-compose profile; gateway degrades gracefully if Langfuse is down (fire-and-forget tracing) |
| Eval cost (LLM-as-judge calls) | small fixed eval set; judge via the free Gemini tier; cache results |

## 6. Sources
- [LLM Guard vs NeMo vs Guardrails AI (2026)](https://dev.to/agdex_ai/best-ai-agent-security-guardrails-tools-in-2026-llm-guard-vs-nemo-vs-guardrails-ai-5e5d) · [Best AI guardrails 2026](https://generalanalysis.com/guides/best-ai-guardrails) · [open-source guardrails](https://www.deepinspect.ai/blog/open-source-llm-guardrails)
- [10 LLM observability tools 2026](https://www.confident-ai.com/knowledge-base/compare/10-llm-observability-tools-to-evaluate-and-monitor-ai-2026) · [eval tools for prompt experimentation 2026](https://www.confident-ai.com/knowledge-base/compare/best-ai-evaluation-tools-for-prompt-experimentation-2026) · [LLM eval frameworks](https://aimultiple.com/llm-eval-tools)
