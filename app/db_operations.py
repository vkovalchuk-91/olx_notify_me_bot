import aiosqlite
from datetime import datetime
from aiogram.types import User

DATABASE_PATH = "olx_notify.db"


# Connect to SQLite database (or create it if it doesn't exist)
async def initialize_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
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

        await db.execute('''
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

        await db.execute('''
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

        await db.commit()


async def is_user_registered(user_telegram_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
        SELECT 1
        FROM user
        WHERE user_telegram_id = ?
        LIMIT 1
        ''', (user_telegram_id,))

        # Fetch the result
        exists = await cursor.fetchone() is not None

        await cursor.close()

    return exists


async def register_new_user(user: User):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        await db.execute('''
            INSERT INTO user (user_telegram_id, username, full_name, first_name, last_name, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            ''', (user.id, user.username, user.full_name, user.first_name, user.last_name, created_at))

        await db.commit()


async def create_new_checker_query(user_telegram_id, query_name, query_url):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor = await db.execute('''
        INSERT INTO checker_query (user_telegram_id, query_name, query_url, is_active, is_deleted, created_at)
        VALUES (?, ?, ?, 1, 0, ?)
        ''', (user_telegram_id, query_name, query_url, created_at))

        await db.commit()

        # Отримати query_id останнього вставленого рядка
        query_id = cursor.lastrowid

    return query_id


async def get_all_active_checker_queries():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
        SELECT query_id, user_telegram_id, query_name, query_url, is_active, is_deleted, created_at
        FROM checker_query
        WHERE is_active = 1 AND is_deleted = 0
        ''')

        rows = await cursor.fetchall()
        await cursor.close()

    active_queries = []
    for row in rows:
        active_queries.append({
            'query_id': row[0],
            'user_telegram_id': row[1],
            'query_name': row[2],
            'query_url': row[3],
            'is_active': row[4],
            'is_deleted': row[5],
            'created_at': row[6]
        })

    return active_queries


async def get_active_checker_queries_by_user(user_telegram_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
        SELECT query_id, user_telegram_id, query_url, is_active, is_deleted, created_at
        FROM checker_query
        WHERE user_telegram_id = ? AND is_active = 1 AND is_deleted = 0
        ''', (user_telegram_id,))

        rows = await cursor.fetchall()
        await cursor.close()

    active_queries = []
    for row in rows:
        active_queries.append({
            'query_id': row[0],
            'user_telegram_id': row[1],
            'query_url': row[2],
            'is_active': row[3],
            'is_deleted': row[4],
            'created_at': row[5]
        })

    return active_queries


async def update_checker_query_is_active(query_id, is_active):
    is_active_int = 1 if is_active else 0

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            UPDATE checker_query
            SET is_active = ?
            WHERE query_id = ?
            ''', (is_active_int, query_id))

        await db.commit()


async def set_checker_query_deleted(query_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
        UPDATE checker_query
        SET is_deleted = 1
        WHERE query_id = ?
        ''', (query_id,))

        await db.commit()


async def has_user_active_checker_queries(user_telegram_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
        SELECT 1
        FROM checker_query
        WHERE user_telegram_id = ? AND is_active = 1 AND is_deleted = 0
        LIMIT 1
        ''', (user_telegram_id,))

        exists = await cursor.fetchone() is not None
        await cursor.close()

    return exists


async def count_active_checker_queries(user_telegram_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
        SELECT COUNT(*)
        FROM checker_query
        WHERE user_telegram_id = ? AND is_active = 1 AND is_deleted = 0
        ''', (user_telegram_id,))

        count = (await cursor.fetchone())[0]
        await cursor.close()

    return int(count)


async def count_inactive_checker_queries(user_telegram_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
        SELECT COUNT(*)
        FROM checker_query
        WHERE user_telegram_id = ? AND is_active = 0 AND is_deleted = 0
        ''', (user_telegram_id,))

        count = (await cursor.fetchone())[0]
        await cursor.close()

    return int(count)


async def check_query_url_exists(user_telegram_id, query_url):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
        SELECT 1
        FROM checker_query
        WHERE user_telegram_id = ? AND query_url = ?
        LIMIT 1
        ''', (user_telegram_id, query_url,))

        exists = await cursor.fetchone() is not None
        await cursor.close()

    return exists


async def create_new_found_ad(query_id, ad_url, ad_description, ad_price, currency):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        await db.execute('''
        INSERT INTO found_ad (query_id, ad_url, ad_description, ad_price, currency, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, 1, ?)
        ''', (query_id, ad_url, ad_description, ad_price, currency, created_at))

        await db.commit()


async def get_all_found_ads(query_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
        SELECT ad_id, query_id, ad_url, ad_description, ad_price, currency, is_active, created_at
        FROM found_ad
        WHERE query_id = ?
        ''', (query_id,))
        rows = await cursor.fetchall()

    # Convert the results into a list of dictionaries
    active_ads = []
    for row in rows:
        active_ads.append({
            'ad_id': row[0],
            'query_id': row[1],
            'ad_url': row[2],
            'ad_description': row[3],
            'ad_price': row[4],
            'currency': row[5],
            'is_active': row[6],
            'created_at': row[7]
        })

    return active_ads


async def update_found_ad_is_active(ad_id, is_active):
    is_active_int = 1 if is_active else 0

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            UPDATE found_ad
            SET is_active = ?
            WHERE ad_id = ?
            ''', (is_active_int, ad_id))

        await db.commit()
