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
        elif rule_type == "es_query":
            await self._evaluate_es_query(rule)

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
        """
        Evaluate ratio-based rule
        Example: error_rate = errors / total_requests
        """
        config = rule.get("config", {})
        numerator_metric = config.get("numerator_metric")
        denominator_metric = config.get("denominator_metric")
        threshold = rule.get("threshold", 0.05)  # Default 5%
        duration = timedelta(minutes=rule["duration_minutes"])

        if not numerator_metric or not denominator_metric:
            logger.warning(f"Ratio rule {rule['id']} missing metrics configuration")
            return

        # Query both metrics
        query = """
            SELECT tenant_id, host,
                   SUM(CASE WHEN metric = $1 THEN value ELSE 0 END) as numerator,
                   SUM(CASE WHEN metric = $2 THEN value ELSE 0 END) as denominator
            FROM (
                SELECT tenant_id, host, '{0}' as metric, COUNT(*) as value
                FROM metrics_process
                WHERE timestamp > NOW() - $3
                  AND status = 'error'
                  AND tenant_id = COALESCE($4, tenant_id)
                GROUP BY tenant_id, host
                UNION ALL
                SELECT tenant_id, host, '{1}' as metric, COUNT(*) as value
                FROM metrics_process
                WHERE timestamp > NOW() - $3
                  AND tenant_id = COALESCE($4, tenant_id)
                GROUP BY tenant_id, host
            ) combined
            GROUP BY tenant_id, host
        """.format(numerator_metric, denominator_metric)

        results = await timescale.fetch_all(
            query,
            numerator_metric,
            denominator_metric,
            duration,
            rule.get("tenant_id")
        )

        for result in results:
            numerator = result.get("numerator", 0)
            denominator = result.get("denominator", 1)

            if denominator > 0:
                ratio = numerator / denominator
                if ratio > threshold:
                    await self._fire_alert(
                        rule,
                        result["tenant_id"],
                        result["host"],
                        ratio,
                        f"{rule['name']}: ratio {ratio:.2%} exceeds {threshold:.2%}"
                    )

    async def _evaluate_anomaly(self, rule: Dict):
        """
        Evaluate anomaly detection rule (network spike detection)
        Detects when current value is N times higher than baseline
        """
        config = rule.get("config", {})
        metric = rule.get("metric", "network_bytes_sent")
        multiplier = config.get("multiplier", 3.0)  # Default 3x baseline
        baseline_minutes = config.get("baseline_minutes", 60)
        duration = timedelta(minutes=rule["duration_minutes"])

        # Table mapping for network metrics
        if "network" in metric:
            table = "metrics_network"
            column = metric.replace("network_", "")
        else:
            return

        # Get baseline (average over longer period)
        baseline_query = f"""
            SELECT tenant_id, host, interface, AVG({column}) as baseline_avg
            FROM {table}
            WHERE timestamp BETWEEN NOW() - INTERVAL '{baseline_minutes} minutes'
                                AND NOW() - INTERVAL '{rule["duration_minutes"]} minutes'
              AND tenant_id = COALESCE($1, tenant_id)
            GROUP BY tenant_id, host, interface
        """

        baselines = await timescale.fetch_all(baseline_query, rule.get("tenant_id"))
        baseline_map = {}
        for b in baselines:
            key = f"{b['tenant_id']}:{b['host']}:{b['interface']}"
            baseline_map[key] = b["baseline_avg"]

        # Get current values
        current_query = f"""
            SELECT tenant_id, host, interface, AVG({column}) as current_avg
            FROM {table}
            WHERE timestamp > NOW() - $1
              AND tenant_id = COALESCE($2, tenant_id)
            GROUP BY tenant_id, host, interface
        """

        current_values = await timescale.fetch_all(
            current_query,
            duration,
            rule.get("tenant_id")
        )

        for curr in current_values:
            key = f"{curr['tenant_id']}:{curr['host']}:{curr['interface']}"
            baseline = baseline_map.get(key, 0)

            if baseline > 0 and curr["current_avg"] > (baseline * multiplier):
                await self._fire_alert(
                    rule,
                    curr["tenant_id"],
                    curr["host"],
                    curr["current_avg"],
                    f"{rule['name']}: {metric} spike detected ({curr['current_avg']:.0f} vs baseline {baseline:.0f})"
                )

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

    async def _evaluate_es_query(self, rule: Dict):
        """
        Evaluate Elasticsearch query-based rule
        Searches logs for specific patterns (e.g., error count threshold)
        """
        from . import elastic

        config = rule.get("config", {})
        es_query = config.get("query")
        threshold = rule.get("threshold", 10)
        duration = timedelta(minutes=rule["duration_minutes"])

        if not es_query:
            logger.warning(f"ES query rule {rule['id']} missing query configuration")
            return

        # Build time-based query
        search_body = {
            "query": {
                "bool": {
                    "must": [
                        es_query,
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": f"now-{rule['duration_minutes']}m",
                                    "lte": "now"
                                }
                            }
                        }
                    ]
                }
            },
            "size": 0,
            "aggs": {
                "by_host": {
                    "terms": {
                        "field": "host.keyword",
                        "size": 100
                    },
                    "aggs": {
                        "by_tenant": {
                            "terms": {
                                "field": "tenant_id.keyword",
                                "size": 1
                            }
                        }
                    }
                }
            }
        }

        try:
            # Query Elasticsearch
            response = await elastic.search(
                index="logs-*",
                body=search_body
            )

            # Process aggregation results
            buckets = response.get("aggregations", {}).get("by_host", {}).get("buckets", [])

            for bucket in buckets:
                host = bucket["key"]
                count = bucket["doc_count"]
                tenant_buckets = bucket.get("by_tenant", {}).get("buckets", [])

                if tenant_buckets:
                    tenant_id = tenant_buckets[0]["key"]
                else:
                    tenant_id = rule.get("tenant_id", "unknown")

                # Check threshold
                if count >= threshold:
                    await self._fire_alert(
                        rule,
                        tenant_id,
                        host,
                        count,
                        f"{rule['name']}: {count} log matches in {rule['duration_minutes']}m"
                    )

        except Exception as e:
            logger.error(f"ES query rule {rule['id']} execution error: {e}")

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
