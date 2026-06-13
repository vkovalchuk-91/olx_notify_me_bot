import logging
from datetime import datetime

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(name='apps.monitors.tasks.check_new_ads_task', bind=True)
def check_new_ads_task(self, source=None):
    from apps.monitors.tasks_logic import run_check_new_ads

    start = datetime.now()
    bot = _get_bot_if_configured()
    logger.info(
        'Started ads check task%s. Telegram notifications: %s',
        f' for source={source}' if source else '',
        'enabled' if bot else 'disabled',
        extra={'job_name': 'check_new_ads'},
    )
    run_check_new_ads(bot, source=source)
    elapsed = datetime.now() - start
    minutes = int(elapsed.total_seconds() // 60)
    seconds = int(elapsed.total_seconds() % 60)
    logger.info(
        'Finished ads check task%s in %s min %s sec',
        f' for source={source}' if source else '',
        minutes,
        seconds,
        extra={'job_name': 'check_new_ads'},
    )


@shared_task(name='apps.monitors.tasks.initialize_query_ads_task', bind=True)
def initialize_query_ads_task(self, query_id):
    from apps.monitors.models import CheckerQuery
    from apps.monitors.services import MonitorService

    start = datetime.now()
    query = CheckerQuery.objects.filter(pk=query_id, is_deleted=False).select_related('user').first()
    if not query:
        logger.warning(
            'Initial monitor parse task: query_id=%s not found or deleted',
            query_id,
            extra={'job_name': 'initialize_query_ads'},
        )
        return

    logger.info(
        'Initial monitor parse task: started for query "%s" (%s): %s',
        query.query_name,
        query.source,
        query.query_url,
        extra={'job_name': 'initialize_query_ads'},
    )
    try:
        import asyncio

        parsed_ads = asyncio.run(MonitorService.parse_ads_for_url(query.query_url)) or []
        saved_count = MonitorService.save_initial_ads(query, parsed_ads)
        query.is_active = True
        query.save(update_fields=['is_active'])
        elapsed = datetime.now() - start
        logger.info(
            'Initial monitor parse task: finished query "%s". Parsed=%s, saved=%s, activated=True, time=%s sec',
            query.query_name,
            len(parsed_ads),
            saved_count,
            int(elapsed.total_seconds()),
            extra={'job_name': 'initialize_query_ads'},
        )
    except Exception:
        logger.exception(
            'Initial monitor parse task: failed for query "%s" (%s). Query remains inactive.',
            query.query_name,
            query.pk,
            extra={'job_name': 'initialize_query_ads'},
        )


def _get_bot_if_configured():
    if not settings.TELEGRAM_TOKEN:
        return None
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    return Bot(token=settings.TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
