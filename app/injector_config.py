import os
from pathlib import Path

import injector
from dotenv import load_dotenv
from app.db.db_interface import DatabaseInterface
from app.db.db_postgres_impl import PostgresDatabase
from app.db.db_sqlite_impl import SQLiteDatabase
from app.insta.db_sqlite_insta_impl import InstaSQLiteDatabase

load_dotenv()
USE_LOCAL_DB = os.getenv("USE_LOCAL_DB", "false").lower() in ["true", "1", "t", "y", "yes"]
LOCAL_DB_NAME = os.getenv("LOCAL_DB_NAME")
DB_CONFIG = {
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME"),
    'host': os.getenv("DB_HOST"),
    'port': os.getenv("DB_PORT")
}
INSTA_LOCAL_DB_NAME = os.getenv("INSTA_LOCAL_DB_NAME")


# Створюємо інжектор
class BotModule(injector.Module):
    def configure(self, binder: injector.Binder):
        # Конфігурація інжектора
        if USE_LOCAL_DB:
            base_dir = Path(__file__).resolve().parent.parent
            database_path = base_dir / LOCAL_DB_NAME
            database = SQLiteDatabase(database_path)
        else:
            database = PostgresDatabase(DB_CONFIG)
        binder.bind(DatabaseInterface, to=database, scope=injector.singleton)


class InstaDBModule(injector.Module):
    def configure(self, binder: injector.Binder):
        # Конфігурація інжектора
        base_dir = Path(__file__).resolve().parent.parent
        database_path = base_dir / INSTA_LOCAL_DB_NAME
        database = InstaSQLiteDatabase(database_path)
        binder.bind(InstaSQLiteDatabase, to=database, scope=injector.singleton)
