"""
License validation service
"""
import asyncio
from datetime import datetime, timedelta
import httpx
import logging
from ..config import settings
from . import timescale

logger = logging.getLogger(__name__)


class LicensingService:
    """License validation and enforcement"""

    def __init__(self):
        self.running = False
        self.check_interval = settings.license_check_interval_hours * 3600
        self.grace_period_days = settings.license_grace_period_days

    async def start(self):
        """Start license checking background task"""
        self.running = True
        logger.info("Licensing service started")

        while self.running:
            try:
                await self.check_all_licenses()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"License check error: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour

    async def stop(self):
        """Stop licensing service"""
        self.running = False
        logger.info("Licensing service stopped")

    async def check_all_licenses(self):
        """Check licenses for all tenants"""
        tenants = await timescale.fetch_all(
            "SELECT * FROM tenants WHERE enabled = TRUE"
        )

        for tenant in tenants:
            try:
                await self.check_tenant_license(tenant)
            except Exception as e:
                logger.error(f"Error checking license for tenant {tenant['id']}: {e}")

    async def check_tenant_license(self, tenant: dict):
        """Check and validate a tenant's license"""
        license_key = tenant.get("license_key")

        if not license_key:
            logger.warning(f"Tenant {tenant['id']} has no license key")
            await self._handle_unlicensed_tenant(tenant)
            return

        # Call license API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.license_api_url}/validate",
                    json={
                        "license_key": license_key,
                        "tenant_id": tenant["id"]
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    result = response.json()

                    if result.get("valid"):
                        # Update license info
                        await timescale.execute_query(
                            """
                            UPDATE tenants
                            SET license_expires_at = $1,
                                license_agent_limit = $2,
                                grace_period_until = NULL
                            WHERE id = $3
                            """,
                            result.get("expires_at"),
                            result.get("agent_limit", 10),
                            tenant["id"]
                        )
                        logger.info(f"License validated for tenant {tenant['id']}")
                    else:
                        await self._handle_invalid_license(tenant)
                else:
                    logger.error(f"License API error for tenant {tenant['id']}: {response.status_code}")

        except httpx.TimeoutException:
            logger.error(f"License API timeout for tenant {tenant['id']}")
        except Exception as e:
            logger.error(f"License validation error for tenant {tenant['id']}: {e}")

    async def _handle_unlicensed_tenant(self, tenant: dict):
        """Handle tenant without license"""
        if not tenant.get("grace_period_until"):
            # Start grace period
            grace_until = datetime.utcnow() + timedelta(days=self.grace_period_days)
            await timescale.execute_query(
                "UPDATE tenants SET grace_period_until = $1 WHERE id = $2",
                grace_until,
                tenant["id"]
            )
            logger.warning(f"Grace period started for tenant {tenant['id']} until {grace_until}")

            # Raise platform alarm (warning)
            await self._raise_platform_alarm(
                tenant["id"],
                "warning",
                "License Missing",
                f"Tenant {tenant['name']} has no license key. Grace period started until {grace_until.strftime('%Y-%m-%d %H:%M UTC')}."
            )
        elif datetime.utcnow() > tenant["grace_period_until"]:
            # Grace period expired, disable tenant
            await timescale.execute_query(
                "UPDATE tenants SET enabled = FALSE WHERE id = $1",
                tenant["id"]
            )
            logger.warning(f"Tenant {tenant['id']} disabled (grace period expired)")

            # Raise platform alarm (critical)
            await self._raise_platform_alarm(
                tenant["id"],
                "critical",
                "Tenant Disabled - License Required",
                f"Tenant {tenant['name']} has been disabled due to missing license. Metrics ingestion blocked."
            )

    async def _handle_invalid_license(self, tenant: dict):
        """Handle tenant with invalid license"""
        expires_at = tenant.get("license_expires_at")

        if expires_at and datetime.utcnow() > expires_at:
            # License expired
            if not tenant.get("grace_period_until"):
                grace_until = datetime.utcnow() + timedelta(days=self.grace_period_days)
                await timescale.execute_query(
                    "UPDATE tenants SET grace_period_until = $1 WHERE id = $2",
                    grace_until,
                    tenant["id"]
                )
                logger.warning(f"License expired for tenant {tenant['id']}, grace period until {grace_until}")

                # Raise platform alarm (error)
                await self._raise_platform_alarm(
                    tenant["id"],
                    "error",
                    "License Expired",
                    f"License for tenant {tenant['name']} expired on {expires_at.strftime('%Y-%m-%d')}. Grace period until {grace_until.strftime('%Y-%m-%d %H:%M UTC')}."
                )
            elif datetime.utcnow() > tenant["grace_period_until"]:
                await timescale.execute_query(
                    "UPDATE tenants SET enabled = FALSE WHERE id = $1",
                    tenant["id"]
                )
                logger.warning(f"Tenant {tenant['id']} disabled (license expired, grace period over)")

                # Raise platform alarm (critical)
                await self._raise_platform_alarm(
                    tenant["id"],
                    "critical",
                    "Tenant Disabled - License Expired",
                    f"Tenant {tenant['name']} disabled. License expired and grace period ended. Metrics ingestion blocked."
                )

    async def _raise_platform_alarm(
        self,
        tenant_id: str,
        severity: str,
        title: str,
        message: str
    ):
        """Raise a platform-level alarm for licensing issues"""
        import hashlib

        # Generate fingerprint for deduplication
        fingerprint = hashlib.sha256(
            f"platform:license:{tenant_id}:{title}".encode()
        ).hexdigest()

        # Check if alert already exists and is unresolved
        existing = await timescale.fetch_one(
            """
            SELECT id FROM alerts
            WHERE fingerprint = $1
            AND resolved_at IS NULL
            AND triggered_at > NOW() - INTERVAL '24 hours'
            """,
            fingerprint
        )

        if existing:
            # Alert already exists, skip
            return

        # Create platform alert
        await timescale.execute_query(
            """
            INSERT INTO alerts (
                rule_id, rule_name, tenant_id, host, severity, message,
                triggered_at, fingerprint
            )
            VALUES (NULL, $1, $2, 'platform', $3, $4, NOW(), $5)
            """,
            title,
            tenant_id,
            severity,
            message,
            fingerprint
        )

        logger.info(f"Platform alarm raised: {title} for tenant {tenant_id}")


# Global instance
_service: LicensingService = None


async def start_licensing_service():
    """Start the global licensing service"""
    global _service
    if not _service:
        _service = LicensingService()
        asyncio.create_task(_service.start())


async def stop_licensing_service():
    """Stop the global licensing service"""
    global _service
    if _service:
        await _service.stop()
