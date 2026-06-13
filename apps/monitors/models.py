from django.db import models

from apps.telegram_users.models import TelegramUser


class QuerySource(models.TextChoices):
    OLX = 'olx', 'OLX'
    RIELTOR = 'rieltor', 'Rieltor'


class CheckerQuery(models.Model):
    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='checker_queries',
        db_column='user_telegram_id',
        to_field='user_telegram_id',
    )
    query_name = models.CharField(max_length=500)
    query_url = models.TextField()
    source = models.CharField(max_length=20, choices=QuerySource.choices, blank=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'checker_query'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'query_url'],
                condition=models.Q(is_deleted=False),
                name='unique_active_query_url_per_user',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.source:
            self.source = detect_source(self.query_url)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.query_name


class FoundAd(models.Model):
    query = models.ForeignKey(
        CheckerQuery,
        on_delete=models.CASCADE,
        related_name='found_ads',
        db_column='query_id',
    )
    ad_url = models.TextField()
    ad_description = models.TextField(blank=True)
    ad_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'found_ad'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['query', 'ad_url'], name='unique_ad_url_per_query'),
        ]

    def __str__(self):
        return self.ad_url


def detect_source(query_url: str) -> str:
    if 'rieltor.ua/' in query_url:
        return QuerySource.RIELTOR
    return QuerySource.OLX
