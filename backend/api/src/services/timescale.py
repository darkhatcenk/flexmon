"""
TimescaleDB connection pool and utilities
"""
import asyncpg
from typing import Optional, List, Dict, Any
from ..config import settings
import logging

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def init_db():
    """Initialize database connection pool"""
    global _pool

    # Parse database URL to extract password from secret if needed
    db_url = settings.database_url

    _pool = await asyncpg.create_pool(
        db_url,
        min_size=5,
        max_size=20,
        command_timeout=60
    )

    logger.info("TimescaleDB connection pool initialized")


async def close_db():
    """Close database connection pool"""
    global _pool
    if _pool:
        await _pool.close()
        logger.info("TimescaleDB connection pool closed")


async def get_connection():
    """Get a connection from the pool"""
    if not _pool:
        raise RuntimeError("Database not initialized")
    return await _pool.acquire()


async def release_connection(conn):
    """Release a connection back to the pool"""
    await _pool.release(conn)


async def execute_query(query: str, *args) -> str:
    """Execute a query without returning results"""
    async with _pool.acquire() as conn:
        result = await conn.execute(query, *args)
        return result


async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    """Fetch a single row"""
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    """Fetch all rows"""
    async with _pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def fetch_val(query: str, *args) -> Any:
    """Fetch a single value"""
    async with _pool.acquire() as conn:
        return await conn.fetchval(query, *args)
