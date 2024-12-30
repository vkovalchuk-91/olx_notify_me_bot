from abc import ABC, abstractmethod
from typing import Any, List, Dict
from aiogram.types import User


class DatabaseInterface(ABC):
    @abstractmethod
    async def is_user_registered(self, user_telegram_id: int) -> bool:
        pass

    @abstractmethod
    async def register_new_user(self, user: User) -> None:
        pass

    @abstractmethod
    async def create_new_checker_query(self, user_telegram_id: int, query_name: str, query_url: str) -> int:
        pass

    @abstractmethod
    async def get_all_active_checker_queries(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_checker_queries_by_user(self, user_telegram_id: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_checker_query_by_id(self, query_id: int) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def update_checker_query_is_active(self, query_id: int, is_active: bool) -> None:
        pass

    @abstractmethod
    async def set_checker_query_deleted(self, query_id: int) -> None:
        pass

    @abstractmethod
    async def has_user_active_checker_queries(self, user_telegram_id: int) -> bool:
        pass

    @abstractmethod
    async def count_active_checker_queries(self, user_telegram_id: int) -> int:
        pass

    @abstractmethod
    async def count_inactive_checker_queries(self, user_telegram_id: int) -> int:
        pass

    @abstractmethod
    async def check_query_url_exists(self, user_telegram_id: int, query_url: str) -> bool:
        pass

    @abstractmethod
    async def check_query_url_is_deleted(self, user_telegram_id: int, query_url: str) -> bool:
        pass

    @abstractmethod
    async def create_new_found_ad(self, query_id: int, ad_url: str, ad_description: str, ad_price: float,
                                  currency: str) -> None:
        pass

    @abstractmethod
    async def get_all_found_ads(self, query_id: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def update_found_ad_is_active(self, ad_id: int, is_active: bool) -> None:
        pass

    @abstractmethod
    async def set_checker_query_non_deleted_and_active(self, query_id) -> None:
        pass

    @abstractmethod
    async def get_user_checker_query_id_by_url(self, user_telegram_id: int, query_url: str) -> int:
        pass
