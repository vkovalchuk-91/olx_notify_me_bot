import logging
import secrets
from datetime import datetime
from typing import Any

from notify_bot.config import Settings
from notify_bot.db_backend import SqliteBackend, create_backend
from notify_bot.models import (
    CheckerQuery,
    FoundAd,
    InstaContent,
    InstaObservedUser,
    InstaSubscription,
    JobLog,
    TelegramUser,
)

logger = logging.getLogger(__name__)

FRESH_SCHEMA_SQLITE = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS telegram_user (
    user_telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    first_name TEXT,
    last_name TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS checker_query (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_telegram_id INTEGER NOT NULL,
    query_name TEXT NOT NULL,
    query_url TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'olx',
    is_active INTEGER NOT NULL DEFAULT 1,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS found_ad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER NOT NULL,
    ad_url TEXT NOT NULL,
    ad_description TEXT NOT NULL DEFAULT '',
    ad_price REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(query_id, ad_url)
);

CREATE TABLE IF NOT EXISTS insta_observed_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS insta_subscription (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_user_id INTEGER NOT NULL,
    user_telegram_id INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(observed_user_id, user_telegram_id)
);

CREATE TABLE IF NOT EXISTS insta_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_user_id INTEGER NOT NULL,
    content_type TEXT NOT NULL,
    media_type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    url TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(observed_user_id, content_type, media_type, file_name)
);

CREATE TABLE IF NOT EXISTS job_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'system',
    message TEXT NOT NULL,
    job_name TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace('Z', '+00:00'))


def _row_user(row: dict) -> TelegramUser:
    return TelegramUser(
        user_telegram_id=row['user_telegram_id'],
        username=row.get('username'),
        full_name=row.get('full_name'),
        first_name=row.get('first_name'),
        last_name=row.get('last_name'),
        is_active=bool(row.get('is_active', 1)),
        is_admin=bool(row.get('is_admin', 0)),
        created_at=_parse_dt(row.get('created_at')),
    )


def _row_query(row: dict, user: TelegramUser | None = None) -> CheckerQuery:
    return CheckerQuery(
        id=row['id'],
        user_telegram_id=row['user_telegram_id'],
        query_name=row['query_name'],
        query_url=row['query_url'],
        source=row['source'],
        is_active=bool(row['is_active']),
        is_deleted=bool(row.get('is_deleted', 0)),
        created_at=_parse_dt(row.get('created_at')),
        user=user,
    )


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._backend: SqliteBackend | None = None
        self._insta_sub_user_col: str | None = None

    def _b(self, value: bool):
        return int(value) if self.settings.use_sqlite else value

    def _not_deleted(self, column: str = 'is_deleted') -> str:
        return f'({column} IS NOT TRUE)'

    def _is_true(self, column: str) -> str:
        return f'({column} IS TRUE)'

    def _now_sql(self) -> str:
        return 'CURRENT_TIMESTAMP' if self.settings.use_sqlite else 'NOW()'

    async def _insta_sub_user_column(self) -> str:
        if self._insta_sub_user_col is None:
            if await self._backend.table_exists('insta_subscription') and not await self._backend.column_exists(
                'insta_subscription', 'user_telegram_id'
            ):
                self._insta_sub_user_col = 'user_id'
            else:
                self._insta_sub_user_col = 'user_telegram_id'
        return self._insta_sub_user_col

    @staticmethod
    def _subscription_telegram_id(row: dict) -> int:
        return row.get('user_telegram_id') or row['user_id']

    async def connect(self) -> 'Database':
        self._backend = await create_backend(self.settings)
        await self._ensure_schema()
        logger.info('Database connected: %s', self.settings.database_label)
        return self

    async def close(self) -> None:
        if self._backend:
            await self._backend.close()
            self._backend = None

    async def _ensure_schema(self) -> None:
        backend = self._backend
        has_telegram_user = await backend.table_exists('telegram_user')
        if not has_telegram_user and self.settings.use_sqlite:
            await backend.executescript(FRESH_SCHEMA_SQLITE)
            return

        admin_type = 'BOOLEAN DEFAULT FALSE' if not self.settings.use_sqlite else 'INTEGER DEFAULT 0'
        deleted_type = 'BOOLEAN DEFAULT FALSE' if not self.settings.use_sqlite else 'INTEGER DEFAULT 0'
        await backend.add_column_if_missing('telegram_user', 'is_admin', admin_type)
        await backend.add_column_if_missing('insta_observed_user', 'is_deleted', deleted_type)

        if not await backend.table_exists('insta_subscription'):
            if self.settings.use_sqlite:
                await backend.execute(
                    """
                    CREATE TABLE IF NOT EXISTS insta_subscription (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        observed_user_id INTEGER NOT NULL,
                        user_telegram_id INTEGER NOT NULL,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        is_deleted INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(observed_user_id, user_telegram_id)
                    )
                    """
                )
            else:
                await backend.execute(
                    """
                    CREATE TABLE IF NOT EXISTS insta_subscription (
                        id SERIAL PRIMARY KEY,
                        observed_user_id INTEGER NOT NULL REFERENCES insta_observed_user(id),
                        user_telegram_id BIGINT NOT NULL REFERENCES telegram_user(user_telegram_id),
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(observed_user_id, user_telegram_id)
                    )
                    """
                )
            await backend.commit()

    async def add_job_log(self, level: str, message: str, source: str = 'system', job_name: str = '') -> None:
        if not await self._backend.table_exists('job_log'):
            return
        columns = await self._backend.fetchall(
            "SELECT column_name FROM information_schema.columns WHERE table_name='job_log'"
            if not self.settings.use_sqlite else "PRAGMA table_info(job_log)"
        )
        if self.settings.use_sqlite:
            has_logger_name = any(row.get('name') == 'logger_name' for row in columns)
        else:
            has_logger_name = any(row.get('column_name') == 'logger_name' for row in columns)

        if has_logger_name:
            await self._backend.execute(
                f'INSERT INTO job_log(level, source, message, job_name, logger_name, created_at) VALUES (?, ?, ?, ?, ?, {self._now_sql()})',
                (level, source, message, job_name, 'notify_bot'),
            )
        else:
            await self._backend.execute(
                f'INSERT INTO job_log(level, source, message, job_name, created_at) VALUES (?, ?, ?, ?, {self._now_sql()})',
                (level, source, message, job_name),
            )
        await self._backend.commit()

    async def get_job_logs(
        self,
        limit: int = 30,
        offset: int = 0,
        level: str | None = None,
        job_name: str | None = None,
    ) -> list[JobLog]:
        if not await self._backend.table_exists('job_log'):
            return []
        query = 'SELECT * FROM job_log'
        params: list[Any] = []
        filters = []
        if level:
            filters.append('level = ?')
            params.append(level)
        if job_name:
            filters.append('job_name = ?')
            params.append(job_name)
        if filters:
            query += ' WHERE ' + ' AND '.join(filters)
        query += ' ORDER BY id DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        rows = await self._backend.fetchall(query, tuple(params))
        return [
            JobLog(
                id=row['id'],
                level=row['level'],
                source=row['source'],
                message=row['message'],
                job_name=row.get('job_name', ''),
                created_at=_parse_dt(row.get('created_at')),
            )
            for row in rows
        ]

    async def count_job_logs(self, level: str | None = None, job_name: str | None = None) -> int:
        if not await self._backend.table_exists('job_log'):
            return 0
        query = 'SELECT COUNT(*) AS cnt FROM job_log'
        params: list[Any] = []
        filters = []
        if level:
            filters.append('level = ?')
            params.append(level)
        if job_name:
            filters.append('job_name = ?')
            params.append(job_name)
        if filters:
            query += ' WHERE ' + ' AND '.join(filters)
        row = await self._backend.fetchone(query, tuple(params))
        return row['cnt'] or 0

    async def upsert_telegram_user(self, telegram_user, is_admin: bool = False) -> TelegramUser:
        admin_case = (
            'CASE WHEN excluded.is_admin IS TRUE THEN TRUE ELSE telegram_user.is_admin END'
            if not self.settings.use_sqlite
            else 'CASE WHEN excluded.is_admin = 1 THEN 1 ELSE telegram_user.is_admin END'
        )
        if self.settings.use_sqlite:
            await self._backend.execute(
                f"""
                INSERT INTO telegram_user(user_telegram_id, username, full_name, first_name, last_name, is_active, is_admin, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_telegram_id) DO UPDATE SET
                    username=excluded.username,
                    full_name=excluded.full_name,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    is_active=?,
                    is_admin={admin_case}
                """,
                (
                    telegram_user.id,
                    telegram_user.username,
                    telegram_user.full_name,
                    telegram_user.first_name,
                    telegram_user.last_name,
                    self._b(True),
                    self._b(is_admin),
                    self._b(True),
                ),
            )
        else:
            await self._backend.execute(
                f"""
                INSERT INTO telegram_user(
                    user_telegram_id, username, full_name, first_name, last_name,
                    is_active, is_admin, created_at, web_registration_code
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?)
                ON CONFLICT(user_telegram_id) DO UPDATE SET
                    username=excluded.username,
                    full_name=excluded.full_name,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    is_active=?,
                    is_admin={admin_case}
                """,
                (
                    telegram_user.id,
                    telegram_user.username,
                    telegram_user.full_name,
                    telegram_user.first_name,
                    telegram_user.last_name,
                    self._b(True),
                    self._b(is_admin),
                    secrets.token_hex(6),
                    self._b(True),
                ),
            )
        await self._backend.commit()
        return await self.get_telegram_user(telegram_user.id)

    async def get_telegram_user(self, user_telegram_id: int) -> TelegramUser | None:
        row = await self._backend.fetchone(
            'SELECT * FROM telegram_user WHERE user_telegram_id = ?',
            (user_telegram_id,),
        )
        return _row_user(row) if row else None

    async def list_telegram_users(self) -> list[TelegramUser]:
        rows = await self._backend.fetchall('SELECT * FROM telegram_user ORDER BY created_at DESC')
        return [_row_user(row) for row in rows]

    async def set_user_active(self, user_telegram_id: int, is_active: bool) -> TelegramUser:
        await self._backend.execute(
            'UPDATE telegram_user SET is_active = ? WHERE user_telegram_id = ?',
            (self._b(is_active), user_telegram_id),
        )
        await self._backend.commit()
        return await self.get_telegram_user(user_telegram_id)

    async def set_user_admin(self, user_telegram_id: int, is_admin: bool) -> TelegramUser:
        await self._backend.execute(
            'UPDATE telegram_user SET is_admin = ? WHERE user_telegram_id = ?',
            (self._b(is_admin), user_telegram_id),
        )
        await self._backend.commit()
        return await self.get_telegram_user(user_telegram_id)

    async def user_exists(self, user_telegram_id: int) -> bool:
        row = await self._backend.fetchone(
            'SELECT 1 FROM telegram_user WHERE user_telegram_id = ?',
            (user_telegram_id,),
        )
        return row is not None

    async def get_user_stats(self, user_telegram_id: int) -> dict[str, int]:
        row = await self._backend.fetchone(
            f"""
            SELECT
                SUM(CASE WHEN {self._is_true('is_active')} THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN {self._is_true('is_active')} THEN 0 ELSE 1 END) AS inactive
            FROM checker_query
            WHERE user_telegram_id = ? AND {self._not_deleted()}
            """,
            (user_telegram_id,),
        )
        return {'active': row['active'] or 0, 'inactive': row['inactive'] or 0}

    async def create_query(
        self,
        user_telegram_id: int,
        query_name: str,
        query_url: str,
        source: str,
        is_active: bool = True,
    ) -> CheckerQuery:
        await self._backend.execute(
            f"""
            INSERT INTO checker_query(user_telegram_id, query_name, query_url, source, is_active, is_deleted, created_at)
            VALUES (?, ?, ?, ?, ?, ?, {self._now_sql()})
            """,
            (user_telegram_id, query_name, query_url, source, self._b(is_active), self._b(False)),
        )
        await self._backend.commit()
        return await self.get_query(self._backend.lastrowid)

    async def get_query(self, query_id: int) -> CheckerQuery | None:
        row = await self._backend.fetchone(
            f'SELECT * FROM checker_query WHERE id = ? AND {self._not_deleted()}',
            (query_id,),
        )
        if not row:
            return None
        user = await self.get_telegram_user(row['user_telegram_id'])
        return _row_query(row, user)

    async def list_queries_for_user(self, user_telegram_id: int, source: str | None = None) -> list[CheckerQuery]:
        if source:
            rows = await self._backend.fetchall(
                f'SELECT * FROM checker_query WHERE user_telegram_id = ? AND source = ? AND {self._not_deleted()} ORDER BY created_at DESC',
                (user_telegram_id, source),
            )
        else:
            rows = await self._backend.fetchall(
                f'SELECT * FROM checker_query WHERE user_telegram_id = ? AND {self._not_deleted()} ORDER BY created_at DESC',
                (user_telegram_id,),
            )
        return [_row_query(row) for row in rows]

    async def list_all_queries(self) -> list[CheckerQuery]:
        rows = await self._backend.fetchall(
            f'SELECT * FROM checker_query WHERE {self._not_deleted()} ORDER BY created_at DESC'
        )
        result = []
        for row in rows:
            user = await self.get_telegram_user(row['user_telegram_id'])
            result.append(_row_query(row, user))
        return result

    async def list_active_queries(self) -> list[CheckerQuery]:
        rows = await self._backend.fetchall(
            f'SELECT * FROM checker_query WHERE {self._is_true("is_active")} AND {self._not_deleted()} ORDER BY created_at DESC'
        )
        result = []
        for row in rows:
            user = await self.get_telegram_user(row['user_telegram_id'])
            result.append(_row_query(row, user))
        return result

    async def toggle_query_active(self, query_id: int) -> CheckerQuery:
        query = await self.get_query(query_id)
        if not query:
            raise ValueError('Query not found')
        await self._backend.execute(
            'UPDATE checker_query SET is_active = ? WHERE id = ?',
            (self._b(not query.is_active), query_id),
        )
        await self._backend.commit()
        return await self.get_query(query_id)

    async def soft_delete_query(self, query_id: int) -> CheckerQuery:
        await self._backend.execute(
            'UPDATE checker_query SET is_deleted = ?, is_active = ? WHERE id = ?',
            (self._b(True), self._b(False), query_id),
        )
        await self._backend.commit()
        row = await self._backend.fetchone('SELECT * FROM checker_query WHERE id = ?', (query_id,))
        return _row_query(row)

    async def query_url_exists(self, user_telegram_id: int, query_url: str) -> bool:
        row = await self._backend.fetchone(
            f'SELECT 1 FROM checker_query WHERE user_telegram_id = ? AND query_url = ? AND {self._not_deleted()}',
            (user_telegram_id, query_url),
        )
        return row is not None

    async def query_url_is_deleted(self, user_telegram_id: int, query_url: str) -> bool:
        row = await self._backend.fetchone(
            f'SELECT 1 FROM checker_query WHERE user_telegram_id = ? AND query_url = ? AND {self._is_true("is_deleted")}',
            (user_telegram_id, query_url),
        )
        return row is not None

    async def restore_query(self, user_telegram_id: int, query_url: str) -> CheckerQuery:
        await self._backend.execute(
            'UPDATE checker_query SET is_deleted = ?, is_active = ? WHERE user_telegram_id = ? AND query_url = ?',
            (self._b(False), self._b(True), user_telegram_id, query_url),
        )
        await self._backend.commit()
        row = await self._backend.fetchone(
            'SELECT * FROM checker_query WHERE user_telegram_id = ? AND query_url = ?',
            (user_telegram_id, query_url),
        )
        return _row_query(row)

    async def activate_query(self, query_id: int) -> None:
        await self._backend.execute(
            'UPDATE checker_query SET is_active = ? WHERE id = ?',
            (self._b(True), query_id),
        )
        await self._backend.commit()

    async def list_found_ads_for_query(self, query_id: int) -> list[FoundAd]:
        rows = await self._backend.fetchall('SELECT * FROM found_ad WHERE query_id = ?', (query_id,))
        return [
            FoundAd(
                id=row['id'],
                query_id=row['query_id'],
                ad_url=row['ad_url'],
                ad_description=row['ad_description'],
                ad_price=float(row['ad_price']),
                currency=row['currency'],
                is_active=bool(row['is_active']),
                created_at=_parse_dt(row.get('created_at')),
            )
            for row in rows
        ]

    async def create_found_ad(self, query_id: int, parsed_ad: dict) -> FoundAd:
        await self._backend.execute(
            f"""
            INSERT INTO found_ad(query_id, ad_url, ad_description, ad_price, currency, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, {self._now_sql()})
            """,
            (
                query_id,
                parsed_ad['ad_url'],
                parsed_ad.get('ad_description', ''),
                float(parsed_ad.get('ad_price', 0) or 0),
                parsed_ad.get('currency', ''),
                self._b(True),
            ),
        )
        await self._backend.commit()
        row = await self._backend.fetchone(
            'SELECT * FROM found_ad WHERE id = ?',
            (self._backend.lastrowid,),
        )
        return FoundAd(
            id=row['id'],
            query_id=row['query_id'],
            ad_url=row['ad_url'],
            ad_description=row['ad_description'],
            ad_price=float(row['ad_price']),
            currency=row['currency'],
            is_active=bool(row['is_active']),
            created_at=_parse_dt(row.get('created_at')),
        )

    async def save_initial_ads(self, query_id: int, parsed_ads: list[dict]) -> int:
        saved = 0
        for ad in parsed_ads:
            row = await self._backend.fetchone(
                'SELECT 1 FROM found_ad WHERE query_id = ? AND ad_url = ?',
                (query_id, ad['ad_url']),
            )
            if row:
                continue
            await self.create_found_ad(query_id, ad)
            saved += 1
        return saved

    async def set_found_ad_active(self, ad_id: int, is_active: bool) -> None:
        await self._backend.execute(
            'UPDATE found_ad SET is_active = ? WHERE id = ?',
            (self._b(is_active), ad_id),
        )
        await self._backend.commit()

    async def list_recent_ads(self, limit: int = 20) -> list[FoundAd]:
        rows = await self._backend.fetchall(
            f'SELECT * FROM found_ad WHERE {self._is_true("is_active")} ORDER BY id DESC LIMIT ?',
            (limit,),
        )
        ads = []
        for row in rows:
            query = await self.get_query(row['query_id'])
            ads.append(
                FoundAd(
                    id=row['id'],
                    query_id=row['query_id'],
                    ad_url=row['ad_url'],
                    ad_description=row['ad_description'],
                    ad_price=float(row['ad_price']),
                    currency=row['currency'],
                    is_active=bool(row['is_active']),
                    created_at=_parse_dt(row.get('created_at')),
                    query=query,
                )
            )
        return ads

    async def get_or_create_insta_user(self, username: str) -> InstaObservedUser:
        normalized = username.strip().lstrip('@')
        row = await self._backend.fetchone(
            'SELECT * FROM insta_observed_user WHERE username = ?',
            (normalized,),
        )
        if row:
            return InstaObservedUser(
                id=row['id'],
                username=row['username'],
                is_active=bool(row['is_active']),
                is_deleted=bool(row.get('is_deleted', 0)),
                created_at=_parse_dt(row.get('created_at')),
            )
        await self._backend.execute(
            f'INSERT INTO insta_observed_user(username, is_active, is_deleted, created_at) VALUES (?, ?, ?, {self._now_sql()})',
            (normalized, self._b(True), self._b(False)),
        )
        await self._backend.commit()
        return InstaObservedUser(
            id=self._backend.lastrowid,
            username=normalized,
            is_active=True,
            is_deleted=False,
        )

    async def get_insta_user(self, user_id: int) -> InstaObservedUser | None:
        row = await self._backend.fetchone(
            f'SELECT * FROM insta_observed_user WHERE id = ? AND {self._not_deleted()}',
            (user_id,),
        )
        if not row:
            return None
        return InstaObservedUser(
            id=row['id'],
            username=row['username'],
            is_active=bool(row['is_active']),
            is_deleted=bool(row.get('is_deleted', 0)),
            created_at=_parse_dt(row.get('created_at')),
        )

    async def add_insta_subscription(self, username: str, user_telegram_id: int) -> tuple[InstaObservedUser, bool, bool]:
        observed_user = await self.get_or_create_insta_user(username)
        created = False
        restored = False
        if observed_user.is_deleted:
            await self._backend.execute(
                'UPDATE insta_observed_user SET is_deleted = ?, is_active = ? WHERE id = ?',
                (self._b(False), self._b(True), observed_user.id),
            )
            restored = True
        user_col = await self._insta_sub_user_column()
        row = await self._backend.fetchone(
            f'SELECT * FROM insta_subscription WHERE observed_user_id = ? AND {user_col} = ?',
            (observed_user.id, user_telegram_id),
        )
        if not row:
            await self._backend.execute(
                f"""
                INSERT INTO insta_subscription(observed_user_id, {user_col}, is_active, is_deleted, created_at)
                VALUES (?, ?, ?, ?, {self._now_sql()})
                """,
                (observed_user.id, user_telegram_id, self._b(True), self._b(False)),
            )
            created = True
        elif row.get('is_deleted') or not row.get('is_active'):
            await self._backend.execute(
                'UPDATE insta_subscription SET is_deleted = ?, is_active = ? WHERE id = ?',
                (self._b(False), self._b(True), row['id']),
            )
            restored = True
        await self._backend.commit()
        observed_user = await self.get_insta_user(observed_user.id)
        return observed_user, created, restored

    async def list_insta_subscriptions(self, user_telegram_id: int | None = None) -> list[InstaSubscription]:
        if not await self._backend.table_exists('insta_subscription'):
            return []
        user_col = await self._insta_sub_user_column()
        query = f"""
            SELECT s.*, s.{user_col} AS user_telegram_id, u.username AS insta_username
            FROM insta_subscription s
            JOIN insta_observed_user u ON u.id = s.observed_user_id
            WHERE {self._not_deleted('s.is_deleted')} AND {self._not_deleted('u.is_deleted')}
        """
        params: list[Any] = []
        if user_telegram_id:
            query += f' AND s.{user_col} = ?'
            params.append(user_telegram_id)
        query += ' ORDER BY u.username'
        rows = await self._backend.fetchall(query, tuple(params))
        result = []
        for row in rows:
            tg_id = self._subscription_telegram_id(row)
            observed_user = InstaObservedUser(
                id=row['observed_user_id'],
                username=row['insta_username'],
                is_active=True,
                is_deleted=False,
            )
            user = await self.get_telegram_user(tg_id)
            result.append(
                InstaSubscription(
                    id=row['id'],
                    observed_user_id=row['observed_user_id'],
                    user_telegram_id=tg_id,
                    is_active=bool(row['is_active']),
                    is_deleted=bool(row.get('is_deleted', 0)),
                    created_at=_parse_dt(row.get('created_at')),
                    observed_user=observed_user,
                    user=user,
                )
            )
        return result

    async def get_insta_subscription(self, subscription_id: int, user_telegram_id: int | None = None) -> InstaSubscription | None:
        for subscription in await self.list_insta_subscriptions(user_telegram_id):
            if subscription.id == subscription_id:
                return subscription
        return None

    async def toggle_insta_subscription(self, subscription_id: int, user_telegram_id: int | None = None) -> InstaSubscription:
        subscription = await self.get_insta_subscription(subscription_id, user_telegram_id)
        if not subscription:
            raise ValueError('Subscription not found')
        await self._backend.execute(
            'UPDATE insta_subscription SET is_active = ? WHERE id = ?',
            (self._b(not subscription.is_active), subscription_id),
        )
        await self._backend.commit()
        return await self.get_insta_subscription(subscription_id, user_telegram_id)

    async def soft_delete_insta_subscription(self, subscription_id: int, user_telegram_id: int | None = None) -> InstaSubscription:
        subscription = await self.get_insta_subscription(subscription_id, user_telegram_id)
        if not subscription:
            raise ValueError('Subscription not found')
        await self._backend.execute(
            'UPDATE insta_subscription SET is_deleted = ?, is_active = ? WHERE id = ?',
            (self._b(True), self._b(False), subscription_id),
        )
        await self._backend.commit()
        return await self.get_insta_subscription(subscription_id, user_telegram_id)

    async def get_active_insta_usernames(self) -> list[str]:
        if await self._backend.table_exists('insta_subscription'):
            user_col = await self._insta_sub_user_column()
            rows = await self._backend.fetchall(
                f"""
                SELECT DISTINCT u.username
                FROM insta_observed_user u
                JOIN insta_subscription s ON s.observed_user_id = u.id
                JOIN telegram_user t ON t.user_telegram_id = s.{user_col}
                WHERE {self._is_true('u.is_active')} AND {self._not_deleted('u.is_deleted')}
                  AND {self._is_true('s.is_active')} AND {self._not_deleted('s.is_deleted')}
                  AND {self._is_true('t.is_active')}
                ORDER BY u.username
                """
            )
            return [row['username'] for row in rows]

        rows = await self._backend.fetchall(
            f"""
            SELECT username
            FROM insta_observed_user
            WHERE {self._is_true('is_active')} AND {self._not_deleted()}
            ORDER BY username
            """
        )
        return [row['username'] for row in rows]

    async def get_insta_subscriber_ids(self, observed_user_id: int) -> list[int]:
        if not await self._backend.table_exists('insta_subscription'):
            return []
        user_col = await self._insta_sub_user_column()
        rows = await self._backend.fetchall(
            f"""
            SELECT s.{user_col} AS user_telegram_id
            FROM insta_subscription s
            JOIN telegram_user t ON t.user_telegram_id = s.{user_col}
            WHERE s.observed_user_id = ? AND {self._is_true('s.is_active')}
              AND {self._not_deleted('s.is_deleted')} AND {self._is_true('t.is_active')}
            """,
            (observed_user_id,),
        )
        return [row['user_telegram_id'] for row in rows]

    async def insta_content_exists(self, observed_user_id: int, content_type: str, media_type: str, file_name: str) -> bool:
        row = await self._backend.fetchone(
            """
            SELECT 1 FROM insta_content
            WHERE observed_user_id = ? AND content_type = ? AND media_type = ? AND file_name = ?
            """,
            (observed_user_id, content_type, media_type, file_name),
        )
        return row is not None

    async def save_insta_content(
        self,
        observed_user_id: int,
        content_type: str,
        media_type: str,
        file_name: str,
        url: str,
    ) -> InstaContent:
        await self._backend.execute(
            f"""
            INSERT INTO insta_content(observed_user_id, content_type, media_type, file_name, url, created_at)
            VALUES (?, ?, ?, ?, ?, {self._now_sql()})
            """,
            (observed_user_id, content_type, media_type, file_name, url),
        )
        await self._backend.commit()
        return InstaContent(
            id=self._backend.lastrowid,
            observed_user_id=observed_user_id,
            content_type=content_type,
            media_type=media_type,
            file_name=file_name,
            url=url,
        )

    async def list_insta_content(self, limit: int = 20) -> list[InstaContent]:
        rows = await self._backend.fetchall(
            'SELECT * FROM insta_content ORDER BY id DESC LIMIT ?',
            (limit,),
        )
        return [
            InstaContent(
                id=row['id'],
                observed_user_id=row['observed_user_id'],
                content_type=row['content_type'],
                media_type=row['media_type'],
                file_name=row['file_name'],
                url=row['url'],
                created_at=_parse_dt(row.get('created_at')),
            )
            for row in rows
        ]

    async def dashboard_stats(self) -> dict[str, int]:
        row = await self._backend.fetchone(
            f"""
            SELECT
                SUM(CASE WHEN {self._is_true('is_active')} THEN 1 ELSE 0 END) AS active_queries,
                SUM(CASE WHEN {self._is_true('is_active')} THEN 0 ELSE 1 END) AS inactive_queries,
                SUM(CASE WHEN source = 'olx' AND {self._is_true('is_active')} THEN 1 ELSE 0 END) AS olx_queries,
                SUM(CASE WHEN source = 'rieltor' AND {self._is_true('is_active')} THEN 1 ELSE 0 END) AS rieltor_queries
            FROM checker_query
            WHERE {self._not_deleted()}
            """
        )
        if await self._backend.table_exists('insta_subscription'):
            insta_row = await self._backend.fetchone(
                f'SELECT COUNT(*) AS cnt FROM insta_subscription WHERE {self._is_true("is_active")} AND {self._not_deleted()}'
            )
            insta_count = insta_row['cnt'] or 0
        else:
            insta_row = await self._backend.fetchone(
                f'SELECT COUNT(*) AS cnt FROM insta_observed_user WHERE {self._is_true("is_active")} AND {self._not_deleted()}'
            )
            insta_count = insta_row['cnt'] or 0
        users_row = await self._backend.fetchone(
            f'SELECT COUNT(*) AS cnt FROM telegram_user WHERE {self._is_true("is_active")}'
        )
        return {
            'active_queries': row['active_queries'] or 0,
            'inactive_queries': row['inactive_queries'] or 0,
            'olx_queries': row['olx_queries'] or 0,
            'rieltor_queries': row['rieltor_queries'] or 0,
            'insta_subscriptions': insta_count,
            'users': users_row['cnt'] or 0,
        }
