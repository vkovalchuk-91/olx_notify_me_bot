import sqlite3
from typing import Any, List, Dict
from datetime import datetime
from aiogram.types import User
import aiosqlite

from app.db.db_interface import DatabaseInterface


class SQLiteDatabase(DatabaseInterface):
    def __init__(self, path):
        self.path = path
        with sqlite3.connect(self.path) as db:
            cursor = db.cursor()

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user (
                user_telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                first_name TEXT,
                last_name TEXT,
                is_active BOOLEAN,
                created_at DATETIME
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS checker_query (
                query_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_telegram_id INTEGER,
                query_name TEXT,
                query_url TEXT,
                is_active BOOLEAN,
                is_deleted BOOLEAN,
                created_at DATETIME,
                FOREIGN KEY (user_telegram_id) REFERENCES user(user_telegram_id)
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS found_ad (
                ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id INTEGER,
                ad_url TEXT,
                ad_description TEXT,
                ad_price REAL,
                currency TEXT,
                is_active BOOLEAN,
                created_at DATETIME,
                FOREIGN KEY (query_id) REFERENCES checker_query(query_id)
            )
            ''')

            db.commit()

    async def is_user_registered(self, user_telegram_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT 1
            FROM user
            WHERE user_telegram_id = ?
            LIMIT 1
            ''', (user_telegram_id,))

            exists = await cursor.fetchone() is not None
            await cursor.close()

        return exists

    async def register_new_user(self, user: User) -> None:
        async with aiosqlite.connect(self.path) as db:
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            await db.execute('''
                INSERT INTO user (user_telegram_id, username, full_name, first_name, last_name, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                ''', (user.id, user.username, user.full_name, user.first_name, user.last_name, created_at))

            await db.commit()

    async def create_new_checker_query(self, user_telegram_id: int, query_name: str, query_url: str) -> int:
        async with aiosqlite.connect(self.path) as db:
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cursor = await db.execute('''
            INSERT INTO checker_query (user_telegram_id, query_name, query_url, is_active, is_deleted, created_at)
            VALUES (?, ?, ?, 1, 0, ?)
            ''', (user_telegram_id, query_name, query_url, created_at))

            await db.commit()
            query_id = cursor.lastrowid

        return query_id

    async def get_all_active_checker_queries(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT query_id, user_telegram_id, query_name, query_url, is_active, is_deleted, created_at
            FROM checker_query
            WHERE is_active = 1 AND is_deleted = 0
            ''')

            rows = await cursor.fetchall()
            await cursor.close()

        return [
            {
                'query_id': row[0],
                'user_telegram_id': row[1],
                'query_name': row[2],
                'query_url': row[3],
                'is_active': row[4],
                'is_deleted': row[5],
                'created_at': row[6]
            }
            for row in rows
        ]

    async def get_checker_queries_by_user(self, user_telegram_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT query_id, user_telegram_id, query_name, query_url, is_active, is_deleted, created_at
            FROM checker_query
            WHERE user_telegram_id = ? AND is_deleted = 0
            ''', (user_telegram_id,))

            rows = await cursor.fetchall()
            await cursor.close()

        return [
            {
                'query_id': row[0],
                'user_telegram_id': row[1],
                'query_name': row[2],
                'query_url': row[3],
                'is_active': row[4],
                'is_deleted': row[5],
                'created_at': row[6]
            }
            for row in rows
        ]

    async def get_checker_query_by_id(self, query_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT * FROM checker_query WHERE query_id = ?
            ''', (query_id,))

            row = await cursor.fetchone()
            await cursor.close()

        return {
            'query_id': row[0],
            'user_telegram_id': row[1],
            'query_name': row[2],
            'query_url': row[3],
            'is_active': row[4],
            'is_deleted': row[5],
            'created_at': row[6]
        }

    async def update_checker_query_is_active(self, query_id: int, is_active: bool) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute('''
                UPDATE checker_query
                SET is_active = ?
                WHERE query_id = ?
                ''', (1 if is_active else 0, query_id))

            await db.commit()

    async def set_checker_query_deleted(self, query_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute('''
            UPDATE checker_query
            SET is_deleted = 1
            WHERE query_id = ?
            ''', (query_id,))

            await db.commit()

    async def has_user_active_checker_queries(self, user_telegram_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT 1
            FROM checker_query
            WHERE user_telegram_id = ? AND is_active = 1 AND is_deleted = 0
            LIMIT 1
            ''', (user_telegram_id,))

            exists = await cursor.fetchone() is not None
            await cursor.close()

        return exists

    async def count_active_checker_queries(self, user_telegram_id: int) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT COUNT(*)
            FROM checker_query
            WHERE user_telegram_id = ? AND is_active = 1 AND is_deleted = 0
            ''', (user_telegram_id,))

            count = (await cursor.fetchone())[0]
            await cursor.close()

        return count

    async def count_inactive_checker_queries(self, user_telegram_id: int) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT COUNT(*)
            FROM checker_query
            WHERE user_telegram_id = ? AND is_active = 0 AND is_deleted = 0
            ''', (user_telegram_id,))

            count = (await cursor.fetchone())[0]
            await cursor.close()

        return count

    async def check_query_url_exists(self, user_telegram_id: int, query_url: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT 1
            FROM checker_query
            WHERE user_telegram_id = ? AND query_url = ?
            LIMIT 1
            ''', (user_telegram_id, query_url))

            exists = await cursor.fetchone() is not None
            await cursor.close()

        return exists

    async def check_query_url_is_deleted(self, user_telegram_id: int, query_url: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT 1
            FROM checker_query
            WHERE user_telegram_id = ? AND query_url = ? AND is_deleted = 1
            LIMIT 1
            ''', (user_telegram_id, query_url))

            exists = await cursor.fetchone() is not None
            await cursor.close()

        return exists

    async def create_new_found_ad(self, query_id: int, ad_url: str, ad_description: str, ad_price: float,
                                  currency: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            await db.execute('''
            INSERT INTO found_ad (query_id, ad_url, ad_description, ad_price, currency, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            ''', (query_id, ad_url, ad_description, ad_price, currency, created_at))

            await db.commit()

    async def get_all_found_ads(self, query_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT ad_id, query_id, ad_url, ad_description, ad_price, currency, is_active, created_at
            FROM found_ad
            WHERE query_id = ?
            ''', (query_id,))

            rows = await cursor.fetchall()

        return [
            {
                'ad_id': row[0],
                'query_id': row[1],
                'ad_url': row[2],
                'ad_description': row[3],
                'ad_price': row[4],
                'currency': row[5],
                'is_active': row[6],
                'created_at': row[7]
            }
            for row in rows
        ]

    async def update_found_ad_is_active(self, ad_id: int, is_active: bool) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute('''
                UPDATE found_ad
                SET is_active = ?
                WHERE ad_id = ?
                ''', (1 if is_active else 0, ad_id))

            await db.commit()

    async def set_checker_query_non_deleted_and_active(self, query_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute('''
            UPDATE checker_query
            SET is_deleted = 0, is_active = 1
            WHERE query_id = ?
            ''', (query_id,))

            await db.commit()

    async def get_user_checker_query_id_by_url(self, user_telegram_id, query_url):
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT query_id
            FROM checker_query
            WHERE user_telegram_id = ? AND query_url = ?
            ''', (user_telegram_id, query_url))

            row = await cursor.fetchone()
            await cursor.close()

        return row[0] if row else None
