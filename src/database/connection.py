"""Database connection management.

This module provides database connection pool and transaction management.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncContextManager, Optional

import asyncpg

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Database connection manager."""

    def __init__(self, connection_string: str, pool_size: int = 10, max_overflow: int = 20):
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        """Initialize database connection pool."""
        try:
            self._pool = await asyncpg.create_pool(
                self.connection_string, min_size=1, max_size=self.pool_size, command_timeout=60
            )
            logger.info(f"資料庫連接池已初始化，池大小: {self.pool_size}")
        except Exception as e:
            logger.error(f"初始化資料庫連接池失敗: {e}")
            raise

    async def close(self) -> None:
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("資料庫連接池已關閉")

    @property
    def pool(self) -> asyncpg.Pool:
        """Get connection pool."""
        if not self._pool:
            raise RuntimeError("資料庫連接池未初始化")
        return self._pool

    @asynccontextmanager
    async def acquire(self) -> AsyncContextManager[asyncpg.Connection]:
        """Acquire database connection from pool."""
        async with self.pool.acquire() as connection:
            yield connection

    @asynccontextmanager
    async def transaction(self) -> AsyncContextManager[asyncpg.Connection]:
        """Get database connection with transaction."""
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                yield connection

    async def execute(self, query: str, *args) -> str:
        """Execute SQL command."""
        async with self.acquire() as connection:
            return await connection.execute(query, *args)

    async def fetch(self, query: str, *args) -> list:
        """Fetch multiple rows."""
        async with self.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch single row."""
        async with self.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        """Fetch single value."""
        async with self.acquire() as connection:
            return await connection.fetchval(query, *args)

    async def executemany(self, query: str, args_list: list) -> None:
        """Execute query multiple times with different arguments."""
        async with self.acquire() as connection:
            await connection.executemany(query, args_list)

    async def copy_to_table(self, table_name: str, source, columns=None) -> str:
        """Copy data to table using COPY command."""
        async with self.acquire() as connection:
            return await connection.copy_to_table(table_name, source=source, columns=columns)

    async def is_connected(self) -> bool:
        """Check if database connection is available."""
        try:
            async with self.acquire() as connection:
                await connection.fetchval("SELECT 1")
            return True
        except Exception:
            return False

    async def get_connection_info(self) -> dict:
        """Get database connection information."""
        if not self._pool:
            return {"status": "未初始化"}

        return {
            "status": "已連接",
            "pool_size": self._pool.get_size(),
            "pool_max_size": self._pool.get_max_size(),
            "pool_min_size": self._pool.get_min_size(),
        }


# Global database connection instance
db: Optional[DatabaseConnection] = None


async def initialize_database(connection_string: str, pool_size: int = 10) -> DatabaseConnection:
    """Initialize global database connection."""
    global db
    db = DatabaseConnection(connection_string, pool_size)
    await db.initialize()
    return db


async def get_database() -> DatabaseConnection:
    """Get global database connection."""
    if not db:
        raise RuntimeError("資料庫連接未初始化")
    return db


async def close_database() -> None:
    """Close global database connection."""
    global db
    if db:
        await db.close()
        db = None
