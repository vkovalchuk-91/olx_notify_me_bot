import re
import secrets
from decimal import Decimal, InvalidOperation
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.monitors.models import CheckerQuery, FoundAd, QuerySource, detect_source
from apps.telegram_users.models import TelegramUser, WebRegistrationRequest
from scrapers import parser_olx
from scrapers.parser_rieltor import parse_rieltor


class IncorrectURL(Exception):
    def __init__(self, message='Введений вами URL є некоректним'):
        self.message = message
        super().__init__(self.message)


class MonitorService:
    @staticmethod
    def register_telegram_user(telegram_user) -> TelegramUser:
        user, _ = TelegramUser.objects.update_or_create(
            user_telegram_id=telegram_user.id,
            defaults={
                'username': telegram_user.username,
                'full_name': telegram_user.full_name,
                'first_name': telegram_user.first_name,
                'last_name': telegram_user.last_name,
                'is_active': True,
            },
        )
        return user

    @staticmethod
    def generate_web_registration_code(telegram_user) -> str:
        user = MonitorService.register_telegram_user(telegram_user)
        code = f'{secrets.randbelow(1_000_000):06d}'
        user.web_registration_code = code
        user.web_registration_code_created_at = timezone.now()
        user.save(update_fields=['web_registration_code', 'web_registration_code_created_at'])
        return code

    @staticmethod
    def create_web_registration_request() -> WebRegistrationRequest:
        return WebRegistrationRequest.objects.create(token=secrets.token_urlsafe(24))

    @staticmethod
    def attach_web_registration_request(token: str, telegram_user) -> tuple[WebRegistrationRequest | None, str]:
        request = WebRegistrationRequest.objects.filter(token=token, is_used=False).first()
        if not request:
            return None, 'registration request not found or already used'
        user = MonitorService.register_telegram_user(telegram_user)
        request.telegram_user = user
        request.save(update_fields=['telegram_user', 'updated_at'])
        return request, ''

    @staticmethod
    def is_user_registered(telegram_id: int) -> bool:
        return TelegramUser.objects.filter(user_telegram_id=telegram_id).exists()

    @staticmethod
    def get_user_stats(telegram_id: int) -> dict:
        active = CheckerQuery.objects.filter(user_id=telegram_id, is_active=True, is_deleted=False).count()
        inactive = CheckerQuery.objects.filter(user_id=telegram_id, is_active=False, is_deleted=False).count()
        return {'active': active, 'inactive': inactive}

    @staticmethod
    def get_checker_queries_for_user(telegram_id: int):
        return list(
            CheckerQuery.objects
            .filter(user_id=telegram_id, is_deleted=False)
            .order_by('-created_at')
        )

    @staticmethod
    def get_checker_query(query_id: int) -> Optional[CheckerQuery]:
        return CheckerQuery.objects.filter(pk=query_id, is_deleted=False).select_related('user').first()

    @staticmethod
    def toggle_query_active(query_id: int) -> CheckerQuery:
        query = CheckerQuery.objects.get(pk=query_id, is_deleted=False)
        query.is_active = not query.is_active
        query.save(update_fields=['is_active'])
        return query

    @staticmethod
    def soft_delete_query(query_id: int) -> CheckerQuery:
        query = CheckerQuery.objects.get(pk=query_id)
        query.is_deleted = True
        query.is_active = False
        query.save(update_fields=['is_deleted', 'is_active'])
        return query

    @staticmethod
    def restore_query(user_id: int, query_url: str) -> CheckerQuery:
        query = CheckerQuery.objects.get(user_id=user_id, query_url=query_url, is_deleted=True)
        query.is_deleted = False
        query.is_active = True
        query.save(update_fields=['is_deleted', 'is_active'])
        return query

    @staticmethod
    def query_url_exists(user_id: int, query_url: str) -> bool:
        return CheckerQuery.objects.filter(user_id=user_id, query_url=query_url, is_deleted=False).exists()

    @staticmethod
    def query_url_is_deleted(user_id: int, query_url: str) -> bool:
        return CheckerQuery.objects.filter(user_id=user_id, query_url=query_url, is_deleted=True).exists()

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

    @staticmethod
    async def parse_ads_for_url(query_url: str):
        source = detect_source(query_url)
        if source == QuerySource.RIELTOR:
            return await parse_rieltor(query_url)
        parsed = await parser_olx.get_parsed_ads({1: query_url})
        return parsed.get(1, [])

    @classmethod
    @transaction.atomic
    def create_query_with_ads(cls, user_id: int, query_name: str, query_url: str, parsed_ads: list) -> CheckerQuery:
        query = cls.create_query(user_id, query_name, query_url)
        cls.save_initial_ads(query, parsed_ads)
        return query

    @staticmethod
    def create_query(user_id: int, query_name: str, query_url: str, is_active: bool = True) -> CheckerQuery:
        return CheckerQuery.objects.create(
            user_id=user_id,
            query_name=query_name,
            query_url=query_url,
            is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def save_initial_ads(query: CheckerQuery, parsed_ads: list) -> int:
        saved_count = 0
        for ad in parsed_ads:
            _, created = FoundAd.objects.get_or_create(
                query=query,
                ad_url=ad['ad_url'],
                defaults={
                    'ad_description': ad.get('ad_description', ''),
                    'ad_price': _normalize_price(ad.get('ad_price', 0)),
                    'currency': ad.get('currency', ''),
                },
            )
            if created:
                saved_count += 1
        return saved_count

    @staticmethod
    def get_active_queries():
        return CheckerQuery.objects.filter(is_active=True, is_deleted=False).select_related('user')

    @staticmethod
    def get_found_ads_for_query(query_id: int):
        return list(FoundAd.objects.filter(query_id=query_id))


def _normalize_price(value) -> Decimal:
    if value in (None, '', 'без ціни'):
        return Decimal('0')
    try:
        cleaned = str(value).replace(' ', '').replace(',', '.')
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal('0')
