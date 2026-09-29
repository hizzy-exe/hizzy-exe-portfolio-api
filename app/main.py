import time
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import redis.asyncio as aioredis
from app.config import settings

app = FastAPI(title="hizzy-exe Proof of Skill API")

# Core Prometheus Metrics
REQUEST_COUNT = Counter("portfolio_requests_total", "Total API Requests", ["method", "endpoint", "http_status"])
REQUEST_LATENCY = Histogram("portfolio_request_latency_seconds", "Request latency", ["endpoint"])

# Initialize Redis Connection Pool
redis_pool = aioredis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
redis_client = aioredis.Redis(connection_pool=redis_pool)

@app.middleware("http")
async def track_and_log_visitor(request: Request, call_next):
    start_time = time.time()
    endpoint = request.url.path
    
    # Bypass tracking for internal metrics evaluation
    if endpoint == "/metrics":
        return await call_next(request)
        
    # Capture user network identity
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host
    user_agent = request.headers.get("User-Agent", "Unknown")

    # Proceed with serving data instantly
    response = await call_next(request)
    
    # Calculate Latency & Record Metrics
    latency = time.time() - start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, http_status=response.status_code).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)

    # Async Offload: Stream metadata to Redis for background lookup
    try:
        payload = {
            "ip": client_ip,
            "user_agent": user_agent,
            "timestamp": time.time(),
            "endpoint": endpoint
        }
        await redis_client.xadd("visitor_stream", {"data": json.dumps(payload)})
    except Exception as e:
        # Prevent analytics failures from hurting customer-facing API execution
        print(f"Failed to stream analytics event async: {e}")

    return response

@app.get("/")
async def get_resume_data():
    """Serves structured resume data back to the user instantly."""
    return JSONResponse(content={
        "owner": "hizzy-exe",
        "role": "Backend & Cloud Engineer",
        "skills": {
            "languages": ["Python", "Go", "Rust", "Solidity"],
            "infrastructure": ["Docker", "Redis Streams", "Prometheus", "AWS"],
            "paradigms": ["Asynchronous Middleware", "Observability", "MLOps"]
        },
        "message": "Your visit has been safely buffered into Redis Streams for background reverse-DNS/GeoIP resolution."
    })

@app.get("/metrics")
async def metrics():
    """Exposes native Prometheus metrics for scraping dashboards."""
    from fastapi import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
