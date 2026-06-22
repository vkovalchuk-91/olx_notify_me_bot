import logging

import httpx
from aiogram import html
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile

from notify_bot.database import Database
from scrapers import parser_olx
from scrapers.insta_parser_anonyig_com import get_parsed_content
from scrapers.parser_rieltor import parse_rieltor

logger = logging.getLogger(__name__)


def _normalize_price(value):
    if value in (None, '', 'без ціни'):
        return 0.0
    try:
        return float(str(value).replace(' ', '').replace(',', '.'))
    except ValueError:
        return 0.0


async def check_new_ads_async(bot, db: Database, source: str | None = None):
    active_queries = await db.list_active_queries()
    if source:
        active_queries = [query for query in active_queries if query.source == source]
    logger.info(
        'Ads check: loaded %s active monitor queries%s',
        len(active_queries),
        f' for source={source}' if source else '',
    )
    await db.add_job_log('INFO', f'Ads check started for {len(active_queries)} queries', job_name='check_new_ads')

    olx_queries = {
        query.id: query.query_url
        for query in active_queries
        if query.source == 'olx' or 'olx.ua/' in query.query_url
    }
    all_olx_parsed_ads = await parser_olx.get_parsed_ads(olx_queries) if olx_queries else {}

    for query in active_queries:
        saved_ads = await db.list_found_ads_for_query(query.id)
        saved_urls = {ad.ad_url for ad in saved_ads}
        deactivated_map = {ad.ad_url: ad for ad in saved_ads if not ad.is_active}

        if query.source == 'olx' or 'olx.ua/' in query.query_url:
            parsed_ads = all_olx_parsed_ads.get(query.id, [])
        elif query.source == 'rieltor' or 'rieltor.ua/' in query.query_url:
            parsed_ads = await parse_rieltor(query.query_url) or []
        else:
            parsed_ads = []

        parsed_urls = {ad['ad_url'] for ad in parsed_ads}
        for parsed_ad in parsed_ads:
            if parsed_ad['ad_url'] not in saved_urls:
                await db.create_found_ad(query.id, {
                    **parsed_ad,
                    'ad_price': _normalize_price(parsed_ad.get('ad_price', 0)),
                })
                if bot:
                    await send_new_ad_notification(bot, parsed_ad, query)
            elif parsed_ad['ad_url'] in deactivated_map:
                await db.set_found_ad_active(deactivated_map[parsed_ad['ad_url']].id, True)

        for ad in saved_ads:
            if ad.ad_url not in parsed_urls and ad.is_active:
                await db.set_found_ad_active(ad.id, False)


async def send_new_ad_notification(bot, parsed_ad, query):
    await bot.send_message(
        query.user_telegram_id,
        f"{html.bold('Додане нове оголошення!')}\n"
        f"{html.bold('Запит: ')}{query.query_name}\n"
        f"{html.bold('Опис: ')}{parsed_ad['ad_description']}\n"
        f"{html.bold('Ціна: ')}{parsed_ad['ad_price']} {parsed_ad['currency']}\n"
        f"{html.bold('URL: ')}{parsed_ad['ad_url']}",
        parse_mode=ParseMode.HTML,
    )


async def initialize_query_ads(bot, db: Database, monitor_service, query_id: int):
    query = await db.get_query(query_id)
    if not query:
        logger.warning('Initial monitor parse: query_id=%s not found', query_id)
        return
    try:
        parsed_ads = await monitor_service.parse_ads_for_url(query.query_url) or []
        saved_count = await db.save_initial_ads(query.id, parsed_ads)
        await db.activate_query(query.id)
        logger.info(
            'Initial monitor parse: finished query "%s". Parsed=%s, saved=%s',
            query.query_name,
            len(parsed_ads),
            saved_count,
        )
        await db.add_job_log(
            'INFO',
            f'Initial parse for "{query.query_name}": parsed={len(parsed_ads)}, saved={saved_count}',
            job_name='initialize_query_ads',
        )
        if bot:
            await bot.send_message(
                query.user_telegram_id,
                f'Первинна перевірка завершена для "{html.bold(query.query_name)}". '
                f'Знайдено {len(parsed_ads)} оголошень.',
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        logger.exception('Initial monitor parse failed for query_id=%s', query_id)
        await db.add_job_log('ERROR', f'Initial parse failed for query_id={query_id}', job_name='initialize_query_ads')


def _map_content_type(value: str) -> str:
    return 'story' if value.lower() == 'story' else 'post'


def _map_media_type(value: str) -> str:
    return 'video' if value.lower() == 'video' else 'photo'


async def check_new_insta_content_async(bot, db: Database):
    usernames = await db.get_active_insta_usernames()
    logger.info('Instagram check: loaded %s active usernames', len(usernames))
    await db.add_job_log('INFO', f'Instagram check started for {len(usernames)} usernames', job_name='check_insta')

    for username in usernames:
        observed_user = await db.get_or_create_insta_user(username)
        try:
            content_items = await get_parsed_content(username, observed_user.id)
        except Exception:
            logger.exception('Instagram check: failed to parse @%s', username)
            await db.add_job_log('ERROR', f'Failed to parse @{username}', job_name='check_insta')
            continue

        for item in content_items:
            content_type = _map_content_type(item['content_type'])
            media_type = _map_media_type(item['media_type'])
            if await db.insta_content_exists(observed_user.id, content_type, media_type, item['file_name']):
                continue
            await db.save_insta_content(
                observed_user.id,
                content_type,
                media_type,
                item['file_name'],
                item['url'],
            )
            if bot:
                subscriber_ids = await db.get_insta_subscriber_ids(observed_user.id)
                for subscriber_id in subscriber_ids:
                    try:
                        await send_insta_notification(bot, item, subscriber_id)
                    except Exception:
                        logger.exception(
                            'Instagram check: failed to notify user %s about @%s',
                            subscriber_id,
                            username,
                        )


async def send_insta_notification(bot, content_item, receiver_id):
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
            await bot.send_video(chat_id=receiver_id, video=media_file, caption=caption, parse_mode=ParseMode.HTML)
        else:
            await bot.send_photo(chat_id=receiver_id, photo=media_file, caption=caption, parse_mode=ParseMode.HTML)
    except Exception:
        logger.exception('Failed to send Instagram media to %s, sending link instead', receiver_id)
        await bot.send_message(
            receiver_id,
            f"{caption}\n{html.link('Open media', url)}",
            parse_mode=ParseMode.HTML,
        )
