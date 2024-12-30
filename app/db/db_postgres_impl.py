from datetime import datetime
from aiogram.types import User
import asyncpg
import psycopg2

from app.db.db_interface import DatabaseInterface


class PostgresDatabase(DatabaseInterface):
    def __init__(self, config):
        self.config = config
        conn = psycopg2.connect(**self.config)
        try:
            with conn.cursor() as cursor:
                # Creating the "user" table
                cursor.execute('''
                        CREATE TABLE IF NOT EXISTS "user" (
                            user_telegram_id BIGINT PRIMARY KEY,
                            username TEXT,
                            full_name TEXT,
                            first_name TEXT,
                            last_name TEXT,
                            is_active BOOLEAN,
                            created_at TIMESTAMP
                        )
                        ''')

                # Creating the "checker_query" table
                cursor.execute('''
                        CREATE TABLE IF NOT EXISTS checker_query (
                            query_id SERIAL PRIMARY KEY,
                            user_telegram_id BIGINT REFERENCES "user"(user_telegram_id),
                            query_name TEXT,
                            query_url TEXT,
                            is_active BOOLEAN,
                            is_deleted BOOLEAN,
                            created_at TIMESTAMP
                        )
                        ''')

                # Creating the "found_ad" table
                cursor.execute('''
                        CREATE TABLE IF NOT EXISTS found_ad (
                            ad_id SERIAL PRIMARY KEY,
                            query_id INTEGER REFERENCES checker_query(query_id),
                            ad_url TEXT,
                            ad_description TEXT,
                            ad_price NUMERIC,
                            currency TEXT,
                            is_active BOOLEAN,
                            created_at TIMESTAMP
                        )
                        ''')

                # Commit changes to the database
                conn.commit()
        finally:
            # Closing the connection
            conn.close()

    async def is_user_registered(self, user_telegram_id):
        conn = await asyncpg.connect(**self.config)
        try:
            result = await conn.fetchval('''
            SELECT 1
            FROM "user"
            WHERE user_telegram_id = $1
            ''', user_telegram_id)
            return result is not None
        finally:
            await conn.close()

    async def register_new_user(self, user: User):
        conn = await asyncpg.connect(**self.config)
        try:
            created_at = datetime.now()
            await conn.execute('''
                INSERT INTO "user" (user_telegram_id, username, full_name, first_name, last_name, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, TRUE, $6)
            ''', user.id, user.username, user.full_name, user.first_name, user.last_name, created_at)
        finally:
            await conn.close()

    async def create_new_checker_query(self, user_telegram_id, query_name, query_url):
        conn = await asyncpg.connect(**self.config)
        try:
            created_at = datetime.now()
            query_id = await conn.fetchval('''
            INSERT INTO checker_query (user_telegram_id, query_name, query_url, is_active, is_deleted, created_at)
            VALUES ($1, $2, $3, TRUE, FALSE, $4)
            RETURNING query_id
            ''', user_telegram_id, query_name, query_url, created_at)
            return query_id
        finally:
            await conn.close()

    async def get_all_active_checker_queries(self):
        conn = await asyncpg.connect(**self.config)
        try:
            rows = await conn.fetch('''
            SELECT query_id, user_telegram_id, query_name, query_url, is_active, is_deleted, created_at
            FROM checker_query
            WHERE is_active = TRUE AND is_deleted = FALSE
            ''')
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    async def get_checker_queries_by_user(self, user_telegram_id):
        conn = await asyncpg.connect(**self.config)
        try:
            rows = await conn.fetch('''
            SELECT query_id, user_telegram_id, query_name, query_url, is_active, is_deleted, created_at
            FROM checker_query
            WHERE user_telegram_id = $1 AND is_deleted = FALSE
            ''', user_telegram_id)
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    async def get_checker_query_by_id(self, query_id):
        conn = await asyncpg.connect(**self.config)
        try:
            row = await conn.fetchrow('''
            SELECT * FROM checker_query WHERE query_id = $1
            ''', query_id)
            return dict(row) if row else None
        finally:
            await conn.close()

    async def update_checker_query_is_active(self, query_id, is_active):
        conn = await asyncpg.connect(**self.config)
        try:
            await conn.execute('''
                UPDATE checker_query
                SET is_active = $1
                WHERE query_id = $2
            ''', is_active, query_id)
        finally:
            await conn.close()

    async def set_checker_query_deleted(self, query_id):
        conn = await asyncpg.connect(**self.config)
        try:
            await conn.execute('''
            UPDATE checker_query
            SET is_deleted = TRUE
            WHERE query_id = $1
            ''', query_id)
        finally:
            await conn.close()

    async def has_user_active_checker_queries(self, user_telegram_id):
        conn = await asyncpg.connect(**self.config)
        try:
            result = await conn.fetchval('''
            SELECT 1
            FROM checker_query
            WHERE user_telegram_id = $1 AND is_active = TRUE AND is_deleted = FALSE
            ''', user_telegram_id)
            return result is not None
        finally:
            await conn.close()

    async def count_active_checker_queries(self, user_telegram_id):
        conn = await asyncpg.connect(**self.config)
        try:
            count = await conn.fetchval('''
            SELECT COUNT(*)
            FROM checker_query
            WHERE user_telegram_id = $1 AND is_active = TRUE AND is_deleted = FALSE
            ''', user_telegram_id)
            return count
        finally:
            await conn.close()

    async def count_inactive_checker_queries(self, user_telegram_id):
        conn = await asyncpg.connect(**self.config)
        try:
            count = await conn.fetchval('''
            SELECT COUNT(*)
            FROM checker_query
            WHERE user_telegram_id = $1 AND is_active = FALSE AND is_deleted = FALSE
            ''', user_telegram_id)
            return count
        finally:
            await conn.close()

    async def check_query_url_exists(self, user_telegram_id, query_url):
        conn = await asyncpg.connect(**self.config)
        try:
            result = await conn.fetchval('''
            SELECT 1
            FROM checker_query
            WHERE user_telegram_id = $1 AND query_url = $2
            ''', user_telegram_id, query_url)
            return result is not None
        finally:
            await conn.close()

    async def check_query_url_is_deleted(self, user_telegram_id, query_url):
        conn = await asyncpg.connect(**self.config)
        try:
            result = await conn.fetchval('''
            SELECT 1
            FROM checker_query
            WHERE user_telegram_id = $1 AND query_url = $2 AND is_deleted = TRUE
            ''', user_telegram_id, query_url)
            return result is not None
        finally:
            await conn.close()

    async def create_new_found_ad(self, query_id, ad_url, ad_description, ad_price, currency):
        conn = await asyncpg.connect(**self.config)
        try:
            created_at = datetime.now()
            await conn.execute('''
            INSERT INTO found_ad (query_id, ad_url, ad_description, ad_price, currency, is_active, created_at)
            VALUES ($1, $2, $3, $4, $5, TRUE, $6)
            ''', query_id, ad_url, ad_description, ad_price, currency, created_at)
        finally:
            await conn.close()

    async def get_all_found_ads(self, query_id):
        conn = await asyncpg.connect(**self.config)
        try:
            rows = await conn.fetch('''
            SELECT ad_id, query_id, ad_url, ad_description, ad_price, currency, is_active, created_at
            FROM found_ad
            WHERE query_id = $1
            ''', query_id)
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    async def update_found_ad_is_active(self, ad_id, is_active):
        conn = await asyncpg.connect(**self.config)
        try:
            await conn.execute('''
                UPDATE found_ad
                SET is_active = $1
                WHERE ad_id = $2
            ''', is_active, ad_id)
        finally:
            await conn.close()

    async def set_checker_query_non_deleted_and_active(self, query_id):
        conn = await asyncpg.connect(**self.config)
        try:
            await conn.execute('''
            UPDATE checker_query
            SET is_deleted = FALSE, is_active = TRUE
            WHERE query_id = $1
            ''', query_id)
        finally:
            await conn.close()

    async def get_user_checker_query_id_by_url(self, user_telegram_id, query_url):
        conn = await asyncpg.connect(**self.config)
        try:
            row = await conn.fetchrow('''
            SELECT query_id
            FROM checker_query
            WHERE user_telegram_id = $1 AND query_url = $2
            ''', user_telegram_id, query_url)
            return row['query_id'] if row else None
        finally:
            await conn.close()
