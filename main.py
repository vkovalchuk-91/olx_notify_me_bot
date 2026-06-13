"""
Legacy entry point. Use Django management commands instead:
  python manage.py run_telegram_bot
  celery -A config worker -l info
  celery -A config beat -l info
  python manage.py runserver
"""
import warnings

warnings.warn(
    'main.py is deprecated. Use Django management commands (see module docstring).',
    DeprecationWarning,
    stacklevel=1,
)

if __name__ == '__main__':
    import os
    import sys
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    print('Use: python manage.py run_telegram_bot', file=sys.stderr)
    sys.exit(1)
