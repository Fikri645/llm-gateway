"""LLM-judged evals (DeepEval) — the model-graded layer above the deterministic
gate. Runs only when a real model key is present (the judge needs an LLM);
in CI / keyless runs it skips, and the deterministic `gate.py` guards instead.

    pytest evals/deepeval_suite.py        # skipped without GEMINI_API_KEY
    GEMINI_API_KEY=... pytest evals/deepeval_suite.py

Metrics: AnswerRelevancy + Faithfulness (hallucination) against the fixed
eval set, judged by Gemini Flash. RAGAS metrics plug in the same way.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src import config, gateway

EVAL_SET = Path(__file__).resolve().parent / "eval_set.jsonl"
needs_key = pytest.mark.skipif(
    not config.GEMINI_API_KEY,
    reason="LLM-judged eval needs GEMINI_API_KEY (deterministic gate.py "
           "guards CI instead)")


def _cases():
    return [json.loads(line) for line in EVAL_SET.read_text().splitlines()
            if line.strip()]


class _GeminiJudge:
    """Minimal DeepEvalBaseLLM wrapper so DeepEval judges with Gemini Flash."""

    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=config.GEMINI_API_KEY)
        self._m = genai.GenerativeModel(config.GEMINI_MODEL)

    def load_model(self):
        return self._m

    def generate(self, prompt: str) -> str:
        return self._m.generate_content(prompt).text

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_name(self):
        return config.GEMINI_MODEL


@needs_key
@pytest.mark.parametrize("case", _cases(), ids=lambda c: c["id"])
def test_answer_relevancy_and_faithfulness(case):
    from deepeval.metrics import (AnswerRelevancyMetric,
                                  FaithfulnessMetric)
    from deepeval.test_case import LLMTestCase

    judge = _GeminiJudge()
    answer = gateway.process(case["question"]).answer
    tc = LLMTestCase(input=case["question"], actual_output=answer,
                     retrieval_context=[case["context"]])

    rel = AnswerRelevancyMetric(threshold=0.7, model=judge)
    faith = FaithfulnessMetric(threshold=0.7, model=judge)
    rel.measure(tc)
    faith.measure(tc)
    assert rel.score >= 0.7, f"relevancy {rel.score}: {rel.reason}"
    assert faith.score >= 0.7, f"faithfulness {faith.score}: {faith.reason}"
