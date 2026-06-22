import asyncio
import logging

from notify_bot.tasks import check_new_ads_async, check_new_insta_content_async

logger = logging.getLogger(__name__)


async def run_scheduler(bot, db, request_interval_minutes: int, insta_interval_minutes: int):
    ads_interval = max(request_interval_minutes, 1) * 60
    insta_interval = max(insta_interval_minutes, 1) * 60
    ads_elapsed = ads_interval
    insta_elapsed = insta_interval

    logger.info(
        'Scheduler started: ads every %s min, instagram every %s min',
        request_interval_minutes,
        insta_interval_minutes,
    )

    while True:
        await asyncio.sleep(30)
        ads_elapsed += 30
        insta_elapsed += 30

        if ads_elapsed >= ads_interval:
            ads_elapsed = 0
            try:
                await check_new_ads_async(bot, db)
            except Exception:
                logger.exception('Scheduled ads check failed')
                await db.add_job_log('ERROR', 'Scheduled ads check failed', job_name='check_new_ads')

        if insta_elapsed >= insta_interval:
            insta_elapsed = 0
            try:
                await check_new_insta_content_async(bot, db)
            except Exception:
                logger.exception('Scheduled Instagram check failed')
                await db.add_job_log('ERROR', 'Scheduled Instagram check failed', job_name='check_insta')
