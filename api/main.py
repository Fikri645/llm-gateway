"""FastAPI surface for the LLM gateway.

POST /chat   {"prompt": "..."}  -> answer + guardrail verdicts + cost + latency
GET  /health
GET  /metrics                    -> rolling p50/p99 latency + cost per 1k

Run:  uvicorn api.main:app --reload
"""
from __future__ import annotations

from collections import deque

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src import gateway

app = FastAPI(title="LLM Gateway", version="1.0")

_lat: deque[float] = deque(maxlen=5000)
_cost: deque[float] = deque(maxlen=5000)


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20000)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    result = gateway.process(req.prompt)
    _lat.append(result.latency_ms)
    _cost.append(result.cost_usd)
    return result.to_dict()


@app.get("/metrics")
def metrics():
    lat = sorted(_lat)
    n = len(lat)
    return {
        "requests": n,
        "latency_p50_ms": lat[n // 2] if n else None,
        "latency_p99_ms": lat[min(int(n * 0.99), n - 1)] if n else None,
        "cost_per_1k_usd": round(sum(_cost) / n * 1000, 4) if n else None,
    }
