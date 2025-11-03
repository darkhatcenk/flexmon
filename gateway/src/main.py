"""
FlexMON Regional Gateway - Forward agent/poller traffic to central API
"""
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import Response, JSONResponse
import httpx
import asyncio
import hmac
import hashlib
from collections import defaultdict
from datetime import datetime
from typing import Optional, List
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FlexMON Regional Gateway",
    version="1.0.0",
    description="Regional gateway for forwarding agent/poller traffic to central API"
)

# Configuration
CENTRAL_API_URL = os.getenv("CENTRAL_API_URL", "http://api:8000")
HMAC_SECRET = os.getenv("HMAC_SECRET", "")
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "1000"))
RATE_LIMIT_PER_IP = int(os.getenv("RATE_LIMIT_PER_IP", "100"))
IP_ALLOWLIST = os.getenv("IP_ALLOWLIST", "").split(",") if os.getenv("IP_ALLOWLIST") else []
ENABLE_HMAC_SIGNING = os.getenv("ENABLE_HMAC_SIGNING", "false").lower() == "true"
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "30"))
GATEWAY_REGION = os.getenv("GATEWAY_REGION", "default")

# Clean up IP allowlist
IP_ALLOWLIST = [ip.strip() for ip in IP_ALLOWLIST if ip.strip()]

# Rate limiting trackers
rate_limit_tracker = defaultdict(list)
request_counter = {"total": 0, "forwarded": 0, "rate_limited": 0, "blocked": 0}

logger.info(f"Gateway starting with config:")
logger.info(f"  Central API: {CENTRAL_API_URL}")
logger.info(f"  HMAC Signing: {ENABLE_HMAC_SIGNING}")
logger.info(f"  Rate Limit (global): {RATE_LIMIT_PER_MIN}/min")
logger.info(f"  Rate Limit (per IP): {RATE_LIMIT_PER_IP}/min")
logger.info(f"  IP Allowlist: {len(IP_ALLOWLIST)} IPs" if IP_ALLOWLIST else "  IP Allowlist: Disabled")
logger.info(f"  Gateway Region: {GATEWAY_REGION}")


def check_ip_allowlist(client_ip: str) -> bool:
    """Check if client IP is in allowlist (if enabled)"""
    if not IP_ALLOWLIST:
        # Allowlist disabled, allow all
        return True

    # Check exact match
    if client_ip in IP_ALLOWLIST:
        return True

    # Check CIDR ranges (basic implementation)
    # For production, use ipaddress module for proper CIDR matching
    for allowed_ip in IP_ALLOWLIST:
        if "*" in allowed_ip:
            # Simple wildcard matching (e.g., 10.0.*)
            pattern = allowed_ip.replace(".", "\\.").replace("*", ".*")
            import re
            if re.match(pattern, client_ip):
                return True

    return False


def check_rate_limit(client_ip: str) -> tuple[bool, str]:
    """
    Check if client is within rate limit
    Returns: (is_allowed, reason)
    """
    now = datetime.now()
    minute_ago = now.timestamp() - 60

    # Clean old entries
    rate_limit_tracker[client_ip] = [
        ts for ts in rate_limit_tracker[client_ip] if ts > minute_ago
    ]

    # Check per-IP limit
    if len(rate_limit_tracker[client_ip]) >= RATE_LIMIT_PER_IP:
        return False, f"Per-IP rate limit exceeded ({RATE_LIMIT_PER_IP}/min)"

    # Check global limit (sum of all IPs)
    total_requests = sum(len(timestamps) for timestamps in rate_limit_tracker.values())
    if total_requests >= RATE_LIMIT_PER_MIN:
        return False, f"Global rate limit exceeded ({RATE_LIMIT_PER_MIN}/min)"

    rate_limit_tracker[client_ip].append(now.timestamp())
    return True, ""


def sign_request(body: bytes) -> str:
    """Generate HMAC signature for request body"""
    if not HMAC_SECRET:
        return ""

    signature = hmac.new(
        HMAC_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    return f"sha256={signature}"


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "flexmon-gateway",
        "region": GATEWAY_REGION,
        "central_api": CENTRAL_API_URL,
        "hmac_enabled": ENABLE_HMAC_SIGNING,
        "ip_allowlist_enabled": len(IP_ALLOWLIST) > 0
    }


@app.get("/stats")
async def stats():
    """Gateway statistics endpoint"""
    return {
        "total_requests": request_counter["total"],
        "forwarded": request_counter["forwarded"],
        "rate_limited": request_counter["rate_limited"],
        "blocked": request_counter["blocked"],
        "active_clients": len(rate_limit_tracker),
        "region": GATEWAY_REGION
    }


@app.middleware("http")
async def gateway_middleware(request: Request, call_next):
    """Middleware for request tracking and IP filtering"""
    request_counter["total"] += 1

    # Skip middleware for health/stats endpoints
    if request.url.path in ["/health", "/stats", "/docs", "/openapi.json"]:
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"

    # Check IP allowlist
    if not check_ip_allowlist(client_ip):
        request_counter["blocked"] += 1
        logger.warning(f"Blocked request from {client_ip} (not in allowlist)")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "IP not allowed"}
        )

    # Check rate limit
    allowed, reason = check_rate_limit(client_ip)
    if not allowed:
        request_counter["rate_limited"] += 1
        logger.warning(f"Rate limited: {client_ip} - {reason}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": reason}
        )

    response = await call_next(request)
    return response


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(path: str, request: Request):
    """
    Proxy all requests to central API with:
    - Rate limiting (per-IP and global)
    - HMAC signing (optional)
    - Retry with exponential backoff
    - IP allowlist (optional)
    """
    client_ip = request.client.host if request.client else "unknown"

    # Build central API URL
    url = f"{CENTRAL_API_URL}/{path}"
    body = await request.body()

    # Prepare headers
    headers = dict(request.headers)
    headers.pop("host", None)  # Remove host header

    # Add gateway metadata
    headers["X-Gateway-Region"] = GATEWAY_REGION
    headers["X-Forwarded-For"] = client_ip
    headers["X-Gateway-Timestamp"] = str(int(datetime.now().timestamp()))

    # Add HMAC signature if enabled
    if ENABLE_HMAC_SIGNING and HMAC_SECRET:
        signature = sign_request(body)
        headers["X-Gateway-Signature"] = signature
        logger.debug(f"Added HMAC signature: {signature[:16]}...")

    # Retry logic with exponential backoff
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                logger.debug(f"Forwarding {request.method} {path} to {url} (attempt {attempt + 1}/{MAX_RETRIES})")

                response = await client.request(
                    method=request.method,
                    url=url,
                    content=body,
                    headers=headers,
                    params=dict(request.query_params)
                )

                request_counter["forwarded"] += 1

                logger.info(
                    f"Forwarded: {request.method} {path} -> {response.status_code} "
                    f"(client={client_ip}, attempt={attempt + 1})"
                )

                # Return response with gateway metadata
                response_headers = dict(response.headers)
                response_headers["X-Gateway-Region"] = GATEWAY_REGION

                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=response_headers
                )

        except httpx.TimeoutException as e:
            last_error = f"Timeout after {TIMEOUT_SECONDS}s"
            logger.warning(f"Timeout on attempt {attempt + 1}/{MAX_RETRIES}: {url}")

        except httpx.ConnectError as e:
            last_error = f"Connection error: {str(e)}"
            logger.warning(f"Connection error on attempt {attempt + 1}/{MAX_RETRIES}: {str(e)}")

        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error on attempt {attempt + 1}/{MAX_RETRIES}: {str(e)}")

        # Exponential backoff (don't wait after last attempt)
        if attempt < MAX_RETRIES - 1:
            backoff_seconds = 2 ** attempt
            logger.debug(f"Backing off for {backoff_seconds}s before retry")
            await asyncio.sleep(backoff_seconds)

    # All retries failed
    logger.error(f"All retries failed for {request.method} {path}: {last_error}")
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Central API unavailable after {MAX_RETRIES} attempts: {last_error}"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info"
    )
