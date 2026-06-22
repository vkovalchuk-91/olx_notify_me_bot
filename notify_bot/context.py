from dataclasses import dataclass

from aiogram import Bot

from notify_bot.config import Settings
from notify_bot.database import Database
from notify_bot.services import InstaMonitorService, MonitorService


@dataclass
class AppContext:
    settings: Settings
    db: Database
    bot: Bot
    monitor_service: MonitorService
    insta_service: InstaMonitorService

    def is_admin(self, telegram_id: int, user=None) -> bool:
        if telegram_id in self.settings.admin_telegram_ids:
            return True
        return bool(user and user.is_admin)
