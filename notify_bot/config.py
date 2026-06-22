import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {'1', 'true', 'yes', 'on'}


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


def _env_ids(name: str) -> set[int]:
    raw = os.getenv(name, '').strip()
    if not raw:
        return set()
    return {int(item.strip()) for item in raw.split(',') if item.strip()}


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    telegram_bot_username: str
    use_sqlite: bool
    sqlite_path: str
    db_host: str
    db_name: str
    db_user: str
    db_password: str
    db_port: int
    admin_telegram_ids: set[int]
    use_async_mode: bool
    workers_number: int
    request_interval_minutes: int
    insta_request_interval_minutes: int

    @classmethod
    def load(cls) -> 'Settings':
        token = os.getenv('TELEGRAM_TOKEN', '').strip()
        if not token:
            raise RuntimeError('TELEGRAM_TOKEN is required')
        if 'USE_SQLITE' in os.environ:
            use_sqlite = _env_bool('USE_SQLITE', True)
        else:
            # legacy Django env: USE_LOCAL_DB=true -> SQLite
            use_sqlite = _env_bool('USE_LOCAL_DB', True)
        return cls(
            telegram_token=token,
            telegram_bot_username=os.getenv('TELEGRAM_BOT_USERNAME', '').strip(),
            use_sqlite=use_sqlite,
            sqlite_path=os.getenv('LOCAL_DB_NAME', 'olx_notify.db'),
            db_host=os.getenv('DB_HOST', '').strip(),
            db_name=os.getenv('DB_NAME', '').strip(),
            db_user=os.getenv('DB_USER', '').strip(),
            db_password=os.getenv('DB_PASSWORD', '').strip(),
            db_port=_env_int('DB_PORT', 5432),
            admin_telegram_ids=_env_ids('ADMIN_TELEGRAM_IDS'),
            use_async_mode=_env_bool('USE_ASYNC_MODE', True),
            workers_number=_env_int('WORKERS_NUMBER', 1),
            request_interval_minutes=_env_int('REQUEST_INTERVAL_MINUTES', 15),
            insta_request_interval_minutes=_env_int('INSTA_REQUEST_INTERVAL_MINUTES', 30),
        )

    @property
    def database_label(self) -> str:
        if self.use_sqlite:
            return self.sqlite_path
        return f'{self.db_host}:{self.db_port}/{self.db_name}'
