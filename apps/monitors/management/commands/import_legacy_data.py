import sqlite3
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.insta_monitor.models import ContentType, InstaContent, InstaObservedUser, MediaType
from apps.monitors.models import CheckerQuery, FoundAd
from apps.telegram_users.models import TelegramUser


class Command(BaseCommand):
    help = 'Import data from legacy SQLite databases'

    def add_arguments(self, parser):
        parser.add_argument('--olx-db', type=str, default='olx_notify.db')
        parser.add_argument('--insta-db', type=str, default='insta_notify.db')

    @transaction.atomic
    def handle(self, *args, **options):
        olx_path = Path(options['olx_db'])
        if olx_path.exists():
            self._import_olx_db(olx_path)
        else:
            self.stdout.write(f'OLX DB not found: {olx_path}')

        insta_path = Path(options['insta_db'])
        if insta_path.exists():
            self._import_insta_db(insta_path)
        else:
            self.stdout.write(f'Insta DB not found: {insta_path}')

    def _import_olx_db(self, path: Path):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        for row in cursor.execute('SELECT * FROM user'):
            TelegramUser.objects.update_or_create(
                user_telegram_id=row['user_telegram_id'],
                defaults={
                    'username': row['username'],
                    'full_name': row['full_name'],
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'is_active': bool(row['is_active']),
                },
            )

        for row in cursor.execute('SELECT * FROM checker_query'):
            CheckerQuery.objects.update_or_create(
                id=row['query_id'],
                defaults={
                    'user_id': row['user_telegram_id'],
                    'query_name': row['query_name'],
                    'query_url': row['query_url'],
                    'is_active': bool(row['is_active']),
                    'is_deleted': bool(row['is_deleted']),
                },
            )

        for row in cursor.execute('SELECT * FROM found_ad'):
            FoundAd.objects.update_or_create(
                id=row['ad_id'],
                defaults={
                    'query_id': row['query_id'],
                    'ad_url': row['ad_url'],
                    'ad_description': row['ad_description'] or '',
                    'ad_price': row['ad_price'] or 0,
                    'currency': row['currency'] or '',
                    'is_active': bool(row['is_active']),
                },
            )

        conn.close()
        self.stdout.write(self.style.SUCCESS(f'Imported OLX data from {path}'))

    def _import_insta_db(self, path: Path):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        content_type_map = {1: ContentType.STORY, 2: ContentType.POST}
        media_type_map = {1: MediaType.PHOTO, 2: MediaType.VIDEO}

        for row in cursor.execute('SELECT * FROM user'):
            InstaObservedUser.objects.update_or_create(
                username=row['username'],
                defaults={'is_active': bool(row['is_active'])},
            )

        for row in cursor.execute('SELECT * FROM content'):
            observed_user = InstaObservedUser.objects.get(username=self._username_by_id(cursor, row['user_id']))
            InstaContent.objects.update_or_create(
                observed_user=observed_user,
                content_type=content_type_map.get(row['content_type_id'], ContentType.POST),
                media_type=media_type_map.get(row['media_type_id'], MediaType.PHOTO),
                file_name=row['file_name'],
                defaults={'url': row['url']},
            )

        conn.close()
        self.stdout.write(self.style.SUCCESS(f'Imported Instagram data from {path}'))

    def _username_by_id(self, cursor, user_id):
        row = cursor.execute('SELECT username FROM user WHERE user_id = ?', (user_id,)).fetchone()
        return row['username'] if row else f'unknown_{user_id}'
