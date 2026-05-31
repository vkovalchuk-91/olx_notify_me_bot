import sqlite3
from datetime import datetime
import aiosqlite


class InstaSQLiteDatabase:
    def __init__(self, path):
        self.path = path
        with sqlite3.connect(self.path) as db:
            cursor = db.cursor()

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                is_active BOOLEAN,
                created_at DATETIME
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_type (
                content_type_id INTEGER PRIMARY KEY,
                content_type TEXT
            )
            ''')

            cursor.executemany('''
                INSERT OR IGNORE INTO content_type (content_type_id, content_type)
                VALUES (?, ?)
            ''', [
                (1, 'Story'),
                (2, 'Post')
            ])

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS media_type (
                media_type_id INTEGER PRIMARY KEY,
                media_type TEXT
            )
            ''')

            cursor.executemany('''
                INSERT OR IGNORE INTO media_type (media_type_id, media_type)
                VALUES (?, ?)
            ''', [
                (1, 'Photo'),
                (2, 'Video')
            ])

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS content (
                content_id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type_id INTEGER,
                media_type_id INTEGER,
                user_id INTEGER,
                file_name TEXT,
                url TEXT,
                created_at DATETIME,
                FOREIGN KEY (content_type_id) REFERENCES content_type(content_type_id),
                FOREIGN KEY (media_type_id) REFERENCES media_type(media_type_id),
                FOREIGN KEY (user_id) REFERENCES user(user_id)
            )
            ''')

            db.commit()

    async def is_user_registered(self, username: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT 1
            FROM user
            WHERE username = ?
            LIMIT 1
            ''', (username,))

            exists = await cursor.fetchone() is not None
            await cursor.close()

        return exists

    async def register_new_user(
            self,
            username: str
    ) -> int:
        async with aiosqlite.connect(self.path) as db:
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cursor = await db.execute('''
                INSERT INTO user (username, is_active, created_at)
                VALUES (?, 1, ?)
                ''', (username, created_at))

            await db.commit()
            new_user_id = cursor.lastrowid

        return new_user_id

    async def get_user_id_by_username(self, username: str) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT user_id
            FROM user
            WHERE username = ?
            ''', (username,))

            row = await cursor.fetchone()
            await cursor.close()

        return row[0] if row else None

    async def get_content_type_id(self, content_type: str) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT content_type_id
            FROM content_type
            WHERE content_type = ?
            ''', (content_type,))

            row = await cursor.fetchone()
            await cursor.close()

        return row[0] if row else None

    async def get_media_type_id(self, media_type: str) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT media_type_id
            FROM media_type
            WHERE media_type = ?
            ''', (media_type,))

            row = await cursor.fetchone()
            await cursor.close()

        return row[0] if row else None

    async def save_new_content(
            self,
            content_type_id: int,
            media_type_id: int,
            user_id: int,
            file_name: str,
            url: str
    ) -> int:
        async with aiosqlite.connect(self.path) as db:
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cursor = await db.execute('''
            INSERT INTO content (content_type_id, media_type_id, user_id, file_name, url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (content_type_id, media_type_id, user_id, file_name, url, created_at))

            await db.commit()
            content_id = cursor.lastrowid

        return content_id

    async def is_content_item_exist(
            self,
            content_type_id: int,
            media_type_id: int,
            user_id: int,
            file_name: str
    ) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT 1
            FROM content
            WHERE content_type_id = ? AND media_type_id = ? AND user_id = ? AND file_name = ?
            LIMIT 1
            ''', (content_type_id, media_type_id, user_id, file_name))

            exists = await cursor.fetchone() is not None
            await cursor.close()

        return exists
