import asyncio
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from asgiref.sync import sync_to_async

from apps.insta_monitor.models import ContentType, InstaContent, InstaObservedUser, InstaSubscription, MediaType
from apps.monitors.models import QuerySource
from apps.telegram_users.models import TelegramUser
from scrapers import parser_olx
from scrapers.insta_parser_anonyig_com import get_parsed_content
from scrapers.parser_rieltor import parse_rieltor

from .models import CheckerQuery, FoundAd
from .services import MonitorService

logger = logging.getLogger(__name__)


async def check_new_ads_async(bot=None, source: str | None = None):
    active_queries = await sync_to_async(list)(MonitorService.get_active_queries())
    if source:
        active_queries = [query for query in active_queries if query.source == source]
    logger.info(
        'Ads check: loaded %s active monitor queries%s',
        len(active_queries),
        f' for source={source}' if source else '',
        extra={'job_name': 'check_new_ads'},
    )
    olx_queries = {
        query.pk: query.query_url
        for query in active_queries
        if query.source == QuerySource.OLX or 'olx.ua/' in query.query_url
    }
    all_olx_parsed_ads = await parser_olx.get_parsed_ads(olx_queries) if olx_queries else {}

    for query in active_queries:
        saved_ads = await sync_to_async(list)(FoundAd.objects.filter(query=query))
        saved_urls = {ad.ad_url for ad in saved_ads}
        deactivated_map = {ad.ad_url: ad for ad in saved_ads if not ad.is_active}

        if query.source == QuerySource.OLX or 'olx.ua/' in query.query_url:
            parsed_ads = all_olx_parsed_ads.get(query.pk, [])
        elif query.source == QuerySource.RIELTOR or 'rieltor.ua/' in query.query_url:
            parsed_ads = await parse_rieltor(query.query_url) or []
        else:
            parsed_ads = []

        logger.info(
            'Ads check: query "%s" (%s) parsed %s ads, already saved %s ads',
            query.query_name,
            query.source,
            len(parsed_ads),
            len(saved_ads),
            extra={'job_name': 'check_new_ads'},
        )
        parsed_urls = {ad['ad_url'] for ad in parsed_ads}

        for parsed_ad in parsed_ads:
            if parsed_ad['ad_url'] not in saved_urls:
                found_ad = await sync_to_async(FoundAd.objects.create)(
                    query=query,
                    ad_url=parsed_ad['ad_url'],
                    ad_description=parsed_ad.get('ad_description', ''),
                    ad_price=_normalize_price(parsed_ad.get('ad_price', 0)),
                    currency=parsed_ad.get('currency', ''),
                )
                logger.info(
                    'Ads check: saved new ad for query "%s": %s | price=%s %s',
                    query.query_name,
                    parsed_ad.get('ad_description', ''),
                    parsed_ad.get('ad_price', 0),
                    parsed_ad.get('currency', ''),
                    extra={'job_name': 'check_new_ads'},
                )
                if bot:
                    await send_new_ad_notification(bot, parsed_ad, query)
                else:
                    await sync_to_async(_create_web_notification)(found_ad, query)
            elif parsed_ad['ad_url'] in deactivated_map:
                ad = deactivated_map[parsed_ad['ad_url']]
                ad.is_active = True
                await sync_to_async(ad.save)(update_fields=['is_active'])
                logger.info(
                    'Ads check: restored previously inactive ad for query "%s": %s',
                    query.query_name,
                    parsed_ad['ad_url'],
                    extra={'job_name': 'check_new_ads'},
                )

        for ad in saved_ads:
            if ad.ad_url not in parsed_urls and ad.is_active:
                ad.is_active = False
                await sync_to_async(ad.save)(update_fields=['is_active'])
                logger.info(
                    'Ads check: marked ad inactive for query "%s": %s',
                    query.query_name,
                    ad.ad_url,
                    extra={'job_name': 'check_new_ads'},
                )


async def send_new_ad_notification(bot, parsed_ad, query: CheckerQuery):
    from aiogram import html
    from aiogram.enums import ParseMode

    logger.info(
        'Telegram notification: sending new ad to user %s for query "%s": %s',
        query.user_id,
        query.query_name,
        parsed_ad['ad_url'],
        extra={'job_name': 'check_new_ads'},
    )
    await bot.send_message(
        query.user_id,
        f"{html.bold('Додане нове оголошення!')}\n"
        f"{html.bold('Запит: ')}{query.query_name}\n"
        f"{html.bold('Опис: ')}{parsed_ad['ad_description']}\n"
        f"{html.bold('Ціна: ')}{parsed_ad['ad_price']} {parsed_ad['currency']}\n"
        f"{html.bold('URL: ')}{parsed_ad['ad_url']}",
        parse_mode=ParseMode.HTML,
    )


def _create_web_notification(found_ad: FoundAd, query: CheckerQuery):
    logger.info(
        'Web notification: new ad found for query "%s": %s',
        query.query_name,
        found_ad.ad_url,
        extra={'job_name': 'check_new_ads'},
    )


def _normalize_price(value) -> Decimal:
    if value in (None, '', 'без ціни'):
        return Decimal('0')
    try:
        return Decimal(str(value).replace(' ', '').replace(',', '.'))
    except (InvalidOperation, ValueError):
        return Decimal('0')


def run_check_new_ads(bot=None, source: str | None = None):
    asyncio.run(check_new_ads_async(bot, source=source))


class InstaMonitorService:
    @staticmethod
    def get_or_create_observed_user(username: str) -> InstaObservedUser:
        user, _ = InstaObservedUser.objects.get_or_create(
            username=normalize_instagram_username(username),
            defaults={'is_active': True, 'is_deleted': False},
        )
        return user

    @staticmethod
    def get_subscriptions_for_management(telegram_user_id: int | None = None):
        subscriptions = (
            InstaSubscription.objects
            .filter(is_deleted=False, observed_user__is_deleted=False)
            .select_related('observed_user', 'user')
            .order_by('observed_user__username', 'user__created_at')
        )
        if telegram_user_id:
            subscriptions = subscriptions.filter(user_id=telegram_user_id)
        return list(subscriptions)

    @staticmethod
    def get_observed_users_for_management():
        return list(
            InstaObservedUser.objects
            .filter(is_deleted=False)
            .prefetch_related('subscriptions__user')
            .order_by('username')
        )

    @staticmethod
    def get_observed_user(user_id: int) -> InstaObservedUser | None:
        return InstaObservedUser.objects.filter(pk=user_id, is_deleted=False).first()

    @staticmethod
    def get_subscription(subscription_id: int, telegram_user_id: int | None = None) -> InstaSubscription | None:
        subscriptions = (
            InstaSubscription.objects
            .filter(pk=subscription_id, is_deleted=False, observed_user__is_deleted=False)
            .select_related('observed_user', 'user')
        )
        if telegram_user_id:
            subscriptions = subscriptions.filter(user_id=telegram_user_id)
        return subscriptions.first()

    @staticmethod
    def add_observed_user(username: str, telegram_user_id: int | None = None) -> tuple[InstaObservedUser, bool, bool]:
        normalized_username = normalize_instagram_username(username)
        user, created = InstaObservedUser.objects.get_or_create(
            username=normalized_username,
            defaults={'is_active': True, 'is_deleted': False},
        )
        restored = False
        if not created and user.is_deleted:
            user.is_deleted = False
            user.is_active = True
            user.save(update_fields=['is_deleted', 'is_active'])
            restored = True
        if telegram_user_id:
            InstaMonitorService.subscribe_user(user, telegram_user_id)
        return user, created, restored

    @staticmethod
    def subscribe_user(observed_user: InstaObservedUser, telegram_user_id: int) -> InstaSubscription:
        telegram_user = TelegramUser.objects.get(pk=telegram_user_id, is_active=True)
        subscription, _ = InstaSubscription.objects.get_or_create(
            observed_user=observed_user,
            user=telegram_user,
            defaults={'is_active': True, 'is_deleted': False},
        )
        if subscription.is_deleted or not subscription.is_active:
            subscription.is_deleted = False
            subscription.is_active = True
            subscription.save(update_fields=['is_deleted', 'is_active'])
        return subscription

    @staticmethod
    def toggle_observed_user_active(user_id: int) -> InstaObservedUser:
        user = InstaObservedUser.objects.get(pk=user_id, is_deleted=False)
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        return user

    @staticmethod
    def toggle_subscription_active(subscription_id: int, telegram_user_id: int | None = None) -> InstaSubscription:
        subscription = InstaMonitorService.get_subscription(subscription_id, telegram_user_id)
        if not subscription:
            raise InstaSubscription.DoesNotExist
        subscription.is_active = not subscription.is_active
        subscription.save(update_fields=['is_active'])
        return subscription

    @staticmethod
    def soft_delete_observed_user(user_id: int) -> InstaObservedUser:
        user = InstaObservedUser.objects.get(pk=user_id)
        user.is_deleted = True
        user.is_active = False
        user.save(update_fields=['is_deleted', 'is_active'])
        return user

    @staticmethod
    def soft_delete_subscription(subscription_id: int, telegram_user_id: int | None = None) -> InstaSubscription:
        subscription = InstaMonitorService.get_subscription(subscription_id, telegram_user_id)
        if not subscription:
            raise InstaSubscription.DoesNotExist
        subscription.is_deleted = True
        subscription.is_active = False
        subscription.save(update_fields=['is_deleted', 'is_active'])
        return subscription

    @staticmethod
    def get_active_observed_usernames() -> list[str]:
        return list(
            InstaObservedUser.objects
            .filter(
                is_active=True,
                is_deleted=False,
                subscriptions__is_active=True,
                subscriptions__is_deleted=False,
                subscriptions__user__is_active=True,
            )
            .values_list('username', flat=True)
            .distinct()
        )

    @staticmethod
    def get_active_subscriber_ids(observed_user: InstaObservedUser) -> list[int]:
        return list(
            observed_user.subscriptions
            .filter(is_active=True, is_deleted=False, user__is_active=True)
            .values_list('user_id', flat=True)
        )

    @staticmethod
    def content_exists(observed_user, content_type, media_type, file_name) -> bool:
        return InstaContent.objects.filter(
            observed_user=observed_user,
            content_type=content_type,
            media_type=media_type,
            file_name=file_name,
        ).exists()

    @staticmethod
    def save_content(observed_user, content_type, media_type, file_name, url) -> InstaContent:
        return InstaContent.objects.create(
            observed_user=observed_user,
            content_type=content_type,
            media_type=media_type,
            file_name=file_name,
            url=url,
        )


async def check_new_insta_content_async(bot=None):
    usernames = await sync_to_async(InstaMonitorService.get_active_observed_usernames)()
    logger.info(
        'Instagram check: loaded %s active usernames: %s',
        len(usernames),
        ', '.join(usernames) or '-',
        extra={'job_name': 'check_insta'},
    )
    for username in usernames:
        observed_user = await sync_to_async(InstaMonitorService.get_or_create_observed_user)(username)
        try:
            logger.info('Instagram check: parsing @%s', username, extra={'job_name': 'check_insta'})
            content_items = await get_parsed_content(username, observed_user.pk)
        except Exception:
            logger.exception(
                'Instagram check: failed to parse @%s, skipping this user',
                username,
                extra={'job_name': 'check_insta'},
            )
            continue
        new_items_count = 0
        skipped_items_count = 0
        for item in content_items:
            content_type = _map_content_type(item['content_type'])
            media_type = _map_media_type(item['media_type'])
            exists = await sync_to_async(InstaMonitorService.content_exists)(
                observed_user, content_type, media_type, item['file_name']
            )
            if exists:
                skipped_items_count += 1
                continue
            insta_content = await sync_to_async(InstaMonitorService.save_content)(
                observed_user, content_type, media_type, item['file_name'], item['url']
            )
            new_items_count += 1
            logger.info(
                'Instagram check: saved new %s %s for @%s: file=%s',
                item['content_type'].lower(),
                item['media_type'].lower(),
                username,
                item['file_name'],
                extra={'job_name': 'check_insta'},
            )
            if bot:
                subscriber_ids = await sync_to_async(InstaMonitorService.get_active_subscriber_ids)(observed_user)
                if not subscriber_ids:
                    logger.info(
                        'Instagram check: new content for @%s has no active Telegram subscribers',
                        username,
                        extra={'job_name': 'check_insta'},
                    )
                for subscriber_id in subscriber_ids:
                    try:
                        await send_insta_notification(bot, item, subscriber_id)
                    except Exception:
                        logger.exception(
                            'Instagram check: failed to notify user %s about @%s content: %s',
                            subscriber_id,
                            username,
                            item.get('url'),
                            extra={'job_name': 'check_insta'},
                        )
            else:
                logger.info(
                    'Instagram check: new content stored without Telegram notification: %s',
                    insta_content.url,
                    extra={'job_name': 'check_insta'},
                )
        logger.info(
            'Instagram check: finished @%s. Parsed=%s, new=%s, already_known=%s',
            username,
            len(content_items),
            new_items_count,
            skipped_items_count,
            extra={'job_name': 'check_insta'},
        )


async def send_insta_notification(bot, content_item, receiver_id):
    import httpx
    from aiogram import html
    from aiogram.enums import ParseMode
    from aiogram.types import BufferedInputFile

    description = (
        f"{content_item['username']} add new "
        f"{content_item['content_type']} {content_item['media_type']}!"
    )
    caption = html.bold(description)
    url = content_item['url']
    is_video = content_item['media_type'] == 'Video'
    filename = content_item.get('file_name') or ('video.mp4' if is_video else 'photo.jpg')

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
            response = await client.get(url)
            response.raise_for_status()
            media_file = BufferedInputFile(response.content, filename=filename)

        if is_video:
            await bot.send_video(
                chat_id=receiver_id,
                video=media_file,
                caption=caption,
                parse_mode=ParseMode.HTML,
            )
        else:
            await bot.send_photo(
                chat_id=receiver_id,
                photo=media_file,
                caption=caption,
                parse_mode=ParseMode.HTML,
            )
        logger.info(
            'Telegram notification: sent Instagram %s "%s" to chat %s',
            content_item['media_type'].lower(),
            filename,
            receiver_id,
            extra={'job_name': 'check_insta'},
        )
    except Exception:
        logger.exception(
            'Telegram notification: failed to send Instagram media file "%s" to chat %s, sending link instead',
            filename,
            receiver_id,
            extra={'job_name': 'check_insta'},
        )
        await bot.send_message(
            receiver_id,
            f"{caption}\n{html.link('Open media', url)}",
            parse_mode=ParseMode.HTML,
        )
        logger.info(
            'Telegram notification: sent Instagram fallback link to chat %s: %s',
            receiver_id,
            url,
            extra={'job_name': 'check_insta'},
        )


def _map_content_type(value: str) -> str:
    return ContentType.STORY if value.lower() == 'story' else ContentType.POST


def _map_media_type(value: str) -> str:
    return MediaType.VIDEO if value.lower() == 'video' else MediaType.PHOTO


def normalize_instagram_username(username: str) -> str:
    return username.strip().lstrip('@')


def run_check_new_insta_content(bot=None):
    asyncio.run(check_new_insta_content_async(bot))
