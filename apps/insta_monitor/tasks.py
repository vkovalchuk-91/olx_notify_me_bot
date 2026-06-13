import logging
from datetime import datetime

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(name='apps.insta_monitor.tasks.check_new_insta_content_task', bind=True)
def check_new_insta_content_task(self):
    from apps.monitors.tasks_logic import run_check_new_insta_content

    start = datetime.now()
    bot = _get_bot_if_configured()
    logger.info(
        'Started Instagram content check task. Telegram notifications: %s',
        'enabled' if bot else 'disabled',
        extra={'job_name': 'check_insta'},
    )
    run_check_new_insta_content(bot)
    elapsed = datetime.now() - start
    minutes = int(elapsed.total_seconds() // 60)
    seconds = int(elapsed.total_seconds() % 60)
    logger.info(
        'Finished Instagram content check task in %s min %s sec',
        minutes,
        seconds,
        extra={'job_name': 'check_insta'},
    )


def _get_bot_if_configured():
    if not settings.TELEGRAM_TOKEN:
        return None
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    return Bot(token=settings.TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
