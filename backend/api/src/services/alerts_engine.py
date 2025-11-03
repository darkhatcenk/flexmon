"""
Alert rule evaluation engine
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
import hashlib
import logging
from . import timescale

logger = logging.getLogger(__name__)


class AlertsEngine:
    """Alert evaluation engine with deduplication"""

    def __init__(self, dedup_minutes: int = 15):
        self.dedup_minutes = dedup_minutes
        self.running = False

    async def start(self):
        """Start alert engine background task"""
        self.running = True
        logger.info("Alerts engine started")

        while self.running:
            try:
                await self.evaluate_all_rules()
                await asyncio.sleep(60)  # Run every minute
            except Exception as e:
                logger.error(f"Alert evaluation error: {e}")
                await asyncio.sleep(60)

    async def stop(self):
        """Stop alert engine"""
        self.running = False
        logger.info("Alerts engine stopped")

    async def evaluate_all_rules(self):
        """Evaluate all enabled alert rules"""
        rules = await timescale.fetch_all(
            "SELECT * FROM alert_rules WHERE enabled = TRUE"
        )

        for rule in rules:
            try:
                await self.evaluate_rule(rule)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule['id']}: {e}")

    async def evaluate_rule(self, rule: Dict):
        """Evaluate a single alert rule"""
        rule_type = rule["type"]

        if rule_type == "threshold":
            await self._evaluate_threshold(rule)
        elif rule_type == "ratio":
            await self._evaluate_ratio(rule)
        elif rule_type == "anomaly":
            await self._evaluate_anomaly(rule)
        elif rule_type == "absence":
            await self._evaluate_absence(rule)

    async def _evaluate_threshold(self, rule: Dict):
        """Evaluate threshold-based rule"""
        # Get metric table
        metric = rule["metric"]
        table_map = {
            "cpu_percent": "metrics_cpu",
            "memory_percent": "metrics_memory",
            "disk_percent": "metrics_disk",
        }

        if metric not in table_map:
            return

        table = table_map[metric]
        duration = timedelta(minutes=rule["duration_minutes"])

        # Query recent metrics
        query = f"""
            SELECT tenant_id, host, AVG({metric}) as avg_value
            FROM {table}
            WHERE timestamp > NOW() - $1
            AND tenant_id = COALESCE($2, tenant_id)
            GROUP BY tenant_id, host
        """

        results = await timescale.fetch_all(
            query,
            duration,
            rule.get("tenant_id")
        )

        # Check threshold
        condition = rule["condition"]
        threshold = rule["threshold"]

        for result in results:
            value = result["avg_value"]
            triggered = False

            if condition == ">" and value > threshold:
                triggered = True
            elif condition == "<" and value < threshold:
                triggered = True
            elif condition == ">=" and value >= threshold:
                triggered = True
            elif condition == "<=" and value <= threshold:
                triggered = True

            if triggered:
                await self._fire_alert(rule, result["tenant_id"], result["host"], value)

    async def _evaluate_ratio(self, rule: Dict):
        """Evaluate ratio-based rule"""
        # TODO: Implement ratio evaluation
        pass

    async def _evaluate_anomaly(self, rule: Dict):
        """Evaluate anomaly detection rule"""
        # TODO: Implement anomaly detection
        pass

    async def _evaluate_absence(self, rule: Dict):
        """Evaluate absence rule (node down)"""
        duration = timedelta(minutes=rule["duration_minutes"])

        query = """
            SELECT DISTINCT a.tenant_id, a.hostname as host
            FROM agents a
            WHERE a.licensed = TRUE
            AND a.last_seen < NOW() - $1
        """

        results = await timescale.fetch_all(query, duration)

        for result in results:
            await self._fire_alert(
                rule,
                result["tenant_id"],
                result["host"],
                None,
                "Node not responding"
            )

    async def _fire_alert(
        self,
        rule: Dict,
        tenant_id: str,
        host: str,
        value: float = None,
        custom_message: str = None
    ):
        """Fire an alert with deduplication"""
        # Generate fingerprint for deduplication
        fingerprint = hashlib.sha256(
            f"{rule['id']}:{tenant_id}:{host}".encode()
        ).hexdigest()

        # Check if alert already exists (not resolved and within dedup window)
        existing = await timescale.fetch_one(
            """
            SELECT id FROM alerts
            WHERE fingerprint = $1
            AND resolved_at IS NULL
            AND triggered_at > NOW() - $2
            """,
            fingerprint,
            timedelta(minutes=self.dedup_minutes)
        )

        if existing:
            # Alert already active, skip
            return

        # Create new alert
        message = custom_message or f"{rule['name']}: {rule['metric']} = {value}"

        await timescale.execute_query(
            """
            INSERT INTO alerts (
                rule_id, rule_name, tenant_id, host, severity, message,
                value, threshold, triggered_at, fingerprint
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), $9)
            """,
            rule["id"],
            rule["name"],
            tenant_id,
            host,
            rule["severity"],
            message,
            value,
            rule.get("threshold"),
            fingerprint
        )

        logger.info(f"Alert fired: {rule['name']} for {host}")


# Global engine instance
_engine: AlertsEngine = None


async def start_alerts_engine():
    """Start the global alerts engine"""
    global _engine
    if not _engine:
        _engine = AlertsEngine()
        asyncio.create_task(_engine.start())


async def stop_alerts_engine():
    """Stop the global alerts engine"""
    global _engine
    if _engine:
        await _engine.stop()
