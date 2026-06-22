import re
from typing import Any

import aiosqlite


def _pg_sql(sql: str) -> str:
    index = 0

    def repl(_: re.Match[str]) -> str:
        nonlocal index
        index += 1
        return f'${index}'

    return re.sub(r'\?', repl, sql)


class SqliteBackend:
    def __init__(self, path: str):
        self.path = path
        self._conn: aiosqlite.Connection | None = None
        self.lastrowid: int | None = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def executescript(self, sql: str) -> None:
        await self._conn.executescript(sql)
        await self._conn.commit()

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        cursor = await self._conn.execute(sql, params)
        self.lastrowid = cursor.lastrowid

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict | None:
        cursor = await self._conn.execute(sql, params)
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict]:
        cursor = await self._conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def commit(self) -> None:
        await self._conn.commit()

    async def table_exists(self, table_name: str) -> bool:
        row = await self.fetchone(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return row is not None

    async def column_exists(self, table_name: str, column_name: str) -> bool:
        rows = await self.fetchall(f'PRAGMA table_info({table_name})')
        return any(row['name'] == column_name for row in rows)

    async def add_column_if_missing(self, table_name: str, column_name: str, definition: str) -> None:
        if not await self.column_exists(table_name, column_name):
            await self.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}')
            await self.commit()


class PostgresBackend:
    def __init__(self, host: str, database: str, user: str, password: str, port: int):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self._pool = None
        self.lastrowid: int | None = None

    async def connect(self) -> None:
        import asyncpg

        self._pool = await asyncpg.create_pool(
            host=self.host,
            database=self.database,
            user=self.user,
            password=self.password,
            port=self.port,
            min_size=1,
            max_size=3,
        )

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def executescript(self, sql: str) -> None:
        statements = [part.strip() for part in sql.split(';') if part.strip()]
        for statement in statements:
            await self.execute(statement)

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        pg_sql = _pg_sql(sql)
        returning = self._insert_returning(pg_sql)
        async with self._pool.acquire() as conn:
            if returning:
                row = await conn.fetchrow(pg_sql + returning, *params)
                self.lastrowid = row['id'] if row else None
            else:
                await conn.execute(pg_sql, *params)
                self.lastrowid = None

    @staticmethod
    def _insert_returning(pg_sql: str) -> str:
        upper = pg_sql.strip().upper()
        if not upper.startswith('INSERT') or 'RETURNING' in upper:
            return ''
        # telegram_user uses user_telegram_id as PK, no serial id column
        if 'INTO TELEGRAM_USER' in upper:
            return ''
        return ' RETURNING id'

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(_pg_sql(sql), *params)
            return dict(row) if row else None

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(_pg_sql(sql), *params)
            return [dict(row) for row in rows]

    async def commit(self) -> None:
        return None

    async def table_exists(self, table_name: str) -> bool:
        row = await self.fetchone(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ?
            """,
            (table_name,),
        )
        return row is not None

    async def column_exists(self, table_name: str, column_name: str) -> bool:
        row = await self.fetchone(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ? AND column_name = ?
            """,
            (table_name, column_name),
        )
        return row is not None

    async def add_column_if_missing(self, table_name: str, column_name: str, definition: str) -> None:
        if not await self.column_exists(table_name, column_name):
            await self.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}')
            await self.commit()


async def create_backend(settings) -> SqliteBackend | PostgresBackend:
    if settings.use_sqlite:
        backend = SqliteBackend(settings.sqlite_path)
    else:
        if not all([settings.db_host, settings.db_name, settings.db_user, settings.db_password]):
            raise RuntimeError('PostgreSQL requires DB_HOST, DB_NAME, DB_USER, DB_PASSWORD')
        backend = PostgresBackend(
            host=settings.db_host,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            port=settings.db_port,
        )
    await backend.connect()
    return backend
