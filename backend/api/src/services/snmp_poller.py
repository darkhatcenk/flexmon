"""
SNMP poller service for network devices
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


class SNMPPoller:
    """SNMP poller for network devices"""

    def __init__(self, interval_sec: int = 60):
        self.interval_sec = interval_sec
        self.running = False

    async def start(self):
        """Start SNMP polling"""
        self.running = True
        logger.info("SNMP poller started")

        while self.running:
            try:
                await self.poll_devices()
                await asyncio.sleep(self.interval_sec)
            except Exception as e:
                logger.error(f"SNMP polling error: {e}")
                await asyncio.sleep(60)

    async def stop(self):
        """Stop SNMP polling"""
        self.running = False
        logger.info("SNMP poller stopped")

    async def poll_devices(self):
        """Poll SNMP devices for metrics"""
        # TODO: Implement SNMP polling
        # - Get list of SNMP devices from DB
        # - Poll standard OIDs (interfaces, system info, etc.)
        # - Store metrics in TimescaleDB
        pass


# Global instance
_poller: SNMPPoller = None


async def start_snmp_poller():
    """Start the SNMP poller"""
    global _poller
    if not _poller:
        _poller = SNMPPoller()
        asyncio.create_task(_poller.start())


async def stop_snmp_poller():
    """Stop the SNMP poller"""
    global _poller
    if _poller:
        await _poller.stop()
