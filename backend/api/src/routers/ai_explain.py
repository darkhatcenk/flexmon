"""
AI-powered alert explanation using Ollama
"""
from fastapi import APIRouter, HTTPException, status, Depends
import httpx
from ..deps.security import get_current_user
from ..config import settings
from ..services import timescale

router = APIRouter()


@router.post("/ai/explain/alert/{alert_id}")
async def explain_alert(
    alert_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get AI-powered explanation for an alert
    """
    # Get alert details
    alert = await timescale.fetch_one(
        "SELECT * FROM alerts WHERE id = $1",
        alert_id
    )

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    # Get recent metrics for context
    metrics_query = """
        SELECT metric_type, value, timestamp
        FROM (
            SELECT 'cpu' as metric_type, cpu_percent as value, timestamp
            FROM metrics_cpu
            WHERE tenant_id = $1 AND host = $2 AND timestamp > NOW() - INTERVAL '1 hour'
            UNION ALL
            SELECT 'memory', memory_percent, timestamp
            FROM metrics_memory
            WHERE tenant_id = $1 AND host = $2 AND timestamp > NOW() - INTERVAL '1 hour'
        ) combined
        ORDER BY timestamp DESC
        LIMIT 100
    """

    metrics = await timescale.fetch_all(
        metrics_query,
        alert["tenant_id"],
        alert["host"]
    )

    # Build context for AI
    context = f"""
Alert: {alert['rule_name']}
Severity: {alert['severity']}
Host: {alert['host']}
Message: {alert['message']}
Current Value: {alert['value']}
Threshold: {alert['threshold']}
Triggered At: {alert['triggered_at']}

Recent Metrics (last hour):
"""

    for m in metrics[:10]:
        context += f"- {m['metric_type']}: {m['value']} at {m['timestamp']}\n"

    # Call AI service
    if not settings.ai_api_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured"
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.ai_api_url}/api/generate",
                json={
                    "model": "llama2",
                    "prompt": f"""You are a system monitoring expert. Analyze this alert and provide:
1. What caused this alert
2. Potential impact on the system
3. Recommended actions

{context}

Provide a concise, actionable explanation in 3-5 sentences.""",
                    "stream": False
                },
                headers={
                    "Authorization": f"Bearer {settings.ai_api_token}"
                }
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI service unavailable"
                )

            result = response.json()
            explanation = result.get("response", "No explanation generated")

            return {
                "alert_id": alert_id,
                "explanation": explanation,
                "context_used": len(metrics),
                "model": "llama2"
            }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI service timeout"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service error: {str(e)}"
        )


@router.post("/ai/explain/metrics")
async def explain_metrics_anomaly(
    host: str,
    metric_type: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get AI explanation for metric anomalies
    """
    # Get recent metrics
    table_map = {
        "cpu": ("metrics_cpu", "cpu_percent"),
        "memory": ("metrics_memory", "memory_percent"),
        "disk": ("metrics_disk", "percent"),
    }

    if metric_type not in table_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid metric type"
        )

    table, column = table_map[metric_type]

    query = f"""
        SELECT timestamp, {column} as value
        FROM {table}
        WHERE tenant_id = $1 AND host = $2
        AND timestamp > NOW() - INTERVAL '24 hours'
        ORDER BY timestamp DESC
    """

    metrics = await timescale.fetch_all(
        query,
        current_user["tenant_id"],
        host
    )

    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No metrics found"
        )

    # Calculate basic statistics
    values = [m["value"] for m in metrics]
    avg = sum(values) / len(values)
    max_val = max(values)
    min_val = min(values)

    context = f"""
Host: {host}
Metric: {metric_type}
Time Range: Last 24 hours
Data Points: {len(metrics)}

Statistics:
- Average: {avg:.2f}
- Maximum: {max_val:.2f}
- Minimum: {min_val:.2f}
- Current: {values[0]:.2f}
"""

    # Call AI service
    if not settings.ai_api_token:
        return {
            "explanation": "AI service not configured. Enable AI analysis in Settings.",
            "statistics": {
                "average": avg,
                "maximum": max_val,
                "minimum": min_val,
                "current": values[0]
            }
        }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.ai_api_url}/api/generate",
                json={
                    "model": "llama2",
                    "prompt": f"""Analyze these system metrics and provide insights:

{context}

Provide:
1. Current system health status
2. Any concerning trends
3. Recommendations if needed

Keep it concise (3-5 sentences).""",
                    "stream": False
                },
                headers={
                    "Authorization": f"Bearer {settings.ai_api_token}"
                }
            )

            if response.status_code == 200:
                result = response.json()
                explanation = result.get("response", "Analysis unavailable")
            else:
                explanation = "AI analysis temporarily unavailable"

            return {
                "host": host,
                "metric_type": metric_type,
                "explanation": explanation,
                "statistics": {
                    "average": avg,
                    "maximum": max_val,
                    "minimum": min_val,
                    "current": values[0]
                }
            }

    except Exception as e:
        return {
            "explanation": f"AI service unavailable: {str(e)}",
            "statistics": {
                "average": avg,
                "maximum": max_val,
                "minimum": min_val,
                "current": values[0]
            }
        }
