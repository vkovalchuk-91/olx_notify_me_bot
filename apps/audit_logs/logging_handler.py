import logging
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='joblog')


def _write_job_log(level, source, logger_name, message, job_name):
    from django.db import close_old_connections

    from apps.audit_logs.models import JobLog

    close_old_connections()
    try:
        JobLog.objects.create(
            level=level,
            source=source,
            logger_name=logger_name,
            message=message,
            job_name=job_name,
        )
    finally:
        close_old_connections()


class DatabaseLogHandler(logging.Handler):
    """Writes log records to JobLog model for admin web UI."""

    SOURCE_MAP = {
        'apps.monitors': 'celery',
        'apps.insta_monitor': 'celery',
        'apps.telegram_bot': 'telegram',
        'scrapers': 'scraper',
    }

    def emit(self, record):
        try:
            from django.apps import apps
            if not apps.ready:
                return

            message = record.getMessage()
            source = self._detect_source(record.name)
            job_name = getattr(record, 'job_name', '') or ''
            level = (
                record.levelname
                if record.levelname in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
                else 'INFO'
            )

            _executor.submit(
                _write_job_log,
                level,
                source,
                record.name,
                message,
                job_name,
            )
        except Exception:
            self.handleError(record)

    def _detect_source(self, logger_name: str) -> str:
        for prefix, source in self.SOURCE_MAP.items():
            if logger_name.startswith(prefix):
                return source
        return 'system'
