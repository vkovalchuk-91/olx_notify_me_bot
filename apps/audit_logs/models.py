from django.db import models


class LogLevel(models.TextChoices):
    DEBUG = 'DEBUG', 'Debug'
    INFO = 'INFO', 'Info'
    WARNING = 'WARNING', 'Warning'
    ERROR = 'ERROR', 'Error'
    CRITICAL = 'CRITICAL', 'Critical'


class LogSource(models.TextChoices):
    CELERY = 'celery', 'Celery'
    TELEGRAM = 'telegram', 'Telegram'
    WEB = 'web', 'Web'
    API = 'api', 'API'
    SCRAPER = 'scraper', 'Scraper'
    SYSTEM = 'system', 'System'


class JobLog(models.Model):
    level = models.CharField(max_length=20, choices=LogLevel.choices, default=LogLevel.INFO)
    source = models.CharField(max_length=20, choices=LogSource.choices, default=LogSource.SYSTEM)
    logger_name = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    job_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'job_log'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.level}] {self.message[:80]}'
