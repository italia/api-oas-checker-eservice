"""
Database initialization and schema management.
Supports PostgreSQL and SQLite (for testing).
"""
import asyncpg
import aiosqlite
import logging
import re
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA_FILE = Path(__file__).parent / "schema.sql"


def load_schema(is_sqlite: bool = False) -> str:
    """
    Load database schema from schema.sql file.
    Performs basic transformations for SQLite compatibility if needed.
    """
    try:
        if not SCHEMA_FILE.exists():
            logger.error(f"Schema file not found: {SCHEMA_FILE}")
            return ""
            
        content = SCHEMA_FILE.read_text(encoding="utf-8")
        
        if is_sqlite:
            # PostgreSQL to SQLite basic conversions
            content = content.replace("JSONB", "TEXT")
            content = content.replace("TIMESTAMP WITH TIME ZONE", "TIMESTAMP")
            content = content.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
            content = content.replace("DEFAULT NOW()", "DEFAULT CURRENT_TIMESTAMP")
            
            # Remove PostgreSQL specific index features (like IF NOT EXISTS if needed, 
            # though SQLite supports it now) and complex indices.
            # Stripping CREATE INDEX for simplicity in SQLite tests.
            lines = []
            for line in content.splitlines():
                if line.strip().upper().startswith("CREATE INDEX"):
                    continue
                lines.append(line)
            content = "\n".join(lines)
            
        return content
    except Exception as e:
        logger.error(f"Error reading schema file: {e}")
        raise


class Database:
    """
    Database manager supporting both PostgreSQL and SQLite.
    Provides connection pooling for PostgreSQL and single connection for SQLite.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None
        self._sqlite_conn: Optional[aiosqlite.Connection] = None
        self.is_sqlite = database_url.startswith("sqlite")

    async def create_pool(self, min_size: int = 2, max_size: int = 10):
        """Initialize connection pool or SQLite connection"""
        if self.is_sqlite:
            if self._sqlite_conn:
                return
            db_path = self.database_url.replace("sqlite:///", "")
            # Ensure parent directory exists for SQLite file
            if db_path and db_path != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                
            self._sqlite_conn = await aiosqlite.connect(db_path)
            self._sqlite_conn.row_factory = aiosqlite.Row
            logger.info(f"SQLite connection established: {db_path}")
            return

        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=min_size,
                max_size=max_size,
                command_timeout=60
            )
            logger.info("PostgreSQL pool created")

    async def close_pool(self):
        """Close all connections"""
        if self._sqlite_conn:
            await self._sqlite_conn.close()
            self._sqlite_conn = None
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def init_db(self):
        """Initialize database schema"""
        schema = load_schema(is_sqlite=self.is_sqlite)
        if not schema:
            return
            
        async with self.get_connection() as conn:
            if self.is_sqlite:
                await conn.executescript(schema)
                await conn.commit()
            else:
                await conn.execute(schema)
            logger.info("Database schema initialized successfully")

    @asynccontextmanager
    async def get_connection(self):
        """
        Get a connection from the pool or the SQLite connection.
        Used as an async context manager.
        """
        if self.is_sqlite:
            if not self._sqlite_conn:
                await self.create_pool()
            yield self._sqlite_conn
            return

        if self._pool is None:
            await self.create_pool()
            
        async with self._pool.acquire() as conn:
            yield conn