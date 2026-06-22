from dataclasses import dataclass
from datetime import datetime


@dataclass
class TelegramUser:
    user_telegram_id: int
    username: str | None
    full_name: str | None
    first_name: str | None
    last_name: str | None
    is_active: bool
    is_admin: bool
    created_at: datetime | None = None


@dataclass
class CheckerQuery:
    id: int
    user_telegram_id: int
    query_name: str
    query_url: str
    source: str
    is_active: bool
    is_deleted: bool
    created_at: datetime | None = None
    user: TelegramUser | None = None


@dataclass
class FoundAd:
    id: int
    query_id: int
    ad_url: str
    ad_description: str
    ad_price: float
    currency: str
    is_active: bool
    created_at: datetime | None = None
    query: CheckerQuery | None = None


@dataclass
class InstaObservedUser:
    id: int
    username: str
    is_active: bool
    is_deleted: bool
    created_at: datetime | None = None


@dataclass
class InstaSubscription:
    id: int
    observed_user_id: int
    user_telegram_id: int
    is_active: bool
    is_deleted: bool
    created_at: datetime | None = None
    observed_user: InstaObservedUser | None = None
    user: TelegramUser | None = None


@dataclass
class InstaContent:
    id: int
    observed_user_id: int
    content_type: str
    media_type: str
    file_name: str
    url: str
    created_at: datetime | None = None


@dataclass
class JobLog:
    id: int
    level: str
    source: str
    message: str
    job_name: str
    created_at: datetime | None = None
