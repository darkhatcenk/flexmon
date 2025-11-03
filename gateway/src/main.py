"""
FlexMON Gateway - Regional proxy with rate limiting and retry
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
import httpx
import asyncio
from collections import defaultdict
from datetime import datetime
import os

app = FastAPI(title="FlexMON Gateway", version="1.0.0")

# Configuration
CENTRAL_API_URL = os.getenv("CENTRAL_API_URL", "http://api:8000")
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "1000"))

# Rate limiting
rate_limit_tracker = defaultdict(list)


def check_rate_limit(client_ip: str) -> bool:
    """Check if client is within rate limit"""
    now = datetime.now()
    minute_ago = now.timestamp() - 60

    # Clean old entries
    rate_limit_tracker[client_ip] = [
        ts for ts in rate_limit_tracker[client_ip] if ts > minute_ago
    ]

    # Check limit
    if len(rate_limit_tracker[client_ip]) >= RATE_LIMIT_PER_MIN:
        return False

    rate_limit_tracker[client_ip].append(now.timestamp())
    return True


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "gateway"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(path: str, request: Request):
    """Proxy all requests to central API with rate limiting and retry"""
    client_ip = request.client.host

    # Check rate limit
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Forward request to central API
    url = f"{CENTRAL_API_URL}/{path}"
    body = await request.body()

    headers = dict(request.headers)
    headers.pop("host", None)

    # Retry logic with exponential backoff
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=request.method,
                    url=url,
                    content=body,
                    headers=headers,
                    params=dict(request.query_params)
                )

                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=503,
                    detail=f"Central API unavailable: {str(e)}"
                )
            # Exponential backoff
            await asyncio.sleep(2 ** attempt)

    raise HTTPException(status_code=503, detail="Central API unavailable")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
