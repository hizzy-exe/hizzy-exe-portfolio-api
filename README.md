# Live Portfolio Metric & Proof of Skill API

> A live portfolio API. Resume data is served on a pure fast path; visitor IP enrichment runs in the background so the public response never waits on DNS or GeoIP.

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)](https://fastapi.tiangolo.com)
[![Redis Streams](https://img.shields.io/badge/Redis-Streams-red)](https://redis.io)
[![Prometheus](https://img.shields.io/badge/Prometheus-metrics-orange)](https://prometheus.io)

---

## What this demonstrates

| Skill | How it shows up |
|-------|-----------------|
| Fast path vs slow path | `GET /` returns resume JSON immediately |
| Async processing | Visitor events are pushed to a **Redis Stream**; a separate worker does the heavy work |
| IP intelligence | Reverse-DNS + MaxMind GeoLite2 run **only** in the worker |
| Observability | Prometheus `/metrics` endpoint |
| Middleware design | Latency tracking + fire-and-forget enqueue |
| Packaging | Docker multi-stage build + docker-compose (API + worker + Redis) |

---

## Architecture

```text
[Visitor] ── HTTP ──> [FastAPI Middleware]
                         │
                         │  1. Record latency / status
                         │  2. XADD minimal event to Redis Stream
                         │  3. Return resume JSON immediately
                         ▼
                   [Redis Stream]
                         │
                         ▼
              [Background Worker]
                 ├── Reverse-DNS lookup
                 ├── MaxMind GeoLite2 (if DB present)
                 └── Log enriched visitor profile
