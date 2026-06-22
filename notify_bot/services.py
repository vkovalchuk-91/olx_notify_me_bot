import re

from scrapers import parser_olx
from scrapers.parser_rieltor import parse_rieltor

from notify_bot.database import Database


class IncorrectURL(Exception):
    def __init__(self, message='Введений вами URL є некоректним'):
        self.message = message
        super().__init__(self.message)


def detect_source(query_url: str) -> str:
    if 'rieltor.ua/' in query_url:
        return 'rieltor'
    return 'olx'


class MonitorService:
    def __init__(self, db: Database):
        self.db = db

    async def register_telegram_user(self, telegram_user, is_admin: bool = False):
        return await self.db.upsert_telegram_user(telegram_user, is_admin=is_admin)

    async def is_user_registered(self, telegram_id: int) -> bool:
        return await self.db.user_exists(telegram_id)

    async def get_user_stats(self, telegram_id: int) -> dict:
        return await self.db.get_user_stats(telegram_id)

    async def get_checker_queries_for_user(self, telegram_id: int, source: str | None = None):
        return await self.db.list_queries_for_user(telegram_id, source=source)

    async def get_checker_query(self, query_id: int):
        return await self.db.get_query(query_id)

    async def toggle_query_active(self, query_id: int):
        return await self.db.toggle_query_active(query_id)

    async def soft_delete_query(self, query_id: int):
        return await self.db.soft_delete_query(query_id)

    async def restore_query(self, user_id: int, query_url: str):
        return await self.db.restore_query(user_id, query_url)

    async def query_url_exists(self, user_id: int, query_url: str) -> bool:
        return await self.db.query_url_exists(user_id, query_url)

    async def query_url_is_deleted(self, user_id: int, query_url: str) -> bool:
        return await self.db.query_url_is_deleted(user_id, query_url)

    @staticmethod
    def is_supported_ads_url(query_url: str) -> bool:
        return 'olx.ua/' in query_url or 'rieltor.ua/' in query_url

    @staticmethod
    def transform_query_text_to_olx_url(text: str) -> str:
        url_prefix = 'https://www.olx.ua/uk/list/q-'
        cleaned_text = text.replace(' ', '-')
        cleaned_text = re.sub(r"[^a-zA-Zа-яА-ЯёЁіїІЇґҐєЄ0-9\.\'\"!\(\)\*\-+,:;=&\^#\$%@-]", '', cleaned_text)
        replacements = {
            '%': '%25', '*': '%2A', '+': '%2B', ',': '%2C', ':': '%3A', ';': '%3B',
            '=': '%3D', '^': '%5E', '#': '%23', '$': '%24', '&': '%26', '@': '%40',
        }
        for old, new in replacements.items():
            cleaned_text = cleaned_text.replace(old, new)
        return url_prefix + cleaned_text + '/'

    async def parse_ads_for_url(self, query_url: str):
        source = detect_source(query_url)
        if source == 'rieltor':
            return await parse_rieltor(query_url)
        parsed = await parser_olx.get_parsed_ads({1: query_url})
        return parsed.get(1, [])

    async def create_query(self, user_id: int, query_name: str, query_url: str, is_active: bool = True):
        return await self.db.create_query(user_id, query_name, query_url, detect_source(query_url), is_active)

    async def save_initial_ads(self, query_id: int, parsed_ads: list) -> int:
        return await self.db.save_initial_ads(query_id, parsed_ads)


class InstaMonitorService:
    def __init__(self, db: Database):
        self.db = db

    async def add_observed_user(self, username: str, telegram_user_id: int | None = None):
        if not telegram_user_id:
            observed_user = await self.db.get_or_create_insta_user(username)
            return observed_user, True, False
        return await self.db.add_insta_subscription(username, telegram_user_id)

    async def get_subscriptions_for_management(self, telegram_user_id: int | None = None):
        return await self.db.list_insta_subscriptions(telegram_user_id)

    async def get_subscription(self, subscription_id: int, telegram_user_id: int | None = None):
        return await self.db.get_insta_subscription(subscription_id, telegram_user_id)

    async def toggle_subscription_active(self, subscription_id: int, telegram_user_id: int | None = None):
        return await self.db.toggle_insta_subscription(subscription_id, telegram_user_id)

    async def soft_delete_subscription(self, subscription_id: int, telegram_user_id: int | None = None):
        return await self.db.soft_delete_insta_subscription(subscription_id, telegram_user_id)
