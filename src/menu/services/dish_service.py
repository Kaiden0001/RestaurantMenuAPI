from typing import Any
from uuid import UUID

from aioredis import Redis
from fastapi import BackgroundTasks

from src.menu.models.dish_model import DishModel
from src.menu.repositories.dish_repository import DishRepository
from src.menu.schemas.dish_schema import DishCreate, DishUpdate
from src.menu.services.cache_service import CacheService


class DishService:
    def __init__(self, dish_repository: DishRepository, redis: Redis, background_tasks: BackgroundTasks):
        self.dish_repository = dish_repository
        self.cache_service: CacheService = CacheService(redis)
        self.background_tasks: BackgroundTasks = background_tasks

    async def get_dishes(self, menu_id: UUID, submenu_id: UUID) -> list[DishModel]:
        """
        Получить список блюд подменю.

        :param menu_id: Идентификатор меню.
        :param submenu_id: Идентификатор подменю.
        :return: Список блюд подменю.
        """
        cache_key: str = f'get_dishes:{menu_id}:{submenu_id}'

        result_cache: list[DishModel] | None = await self.cache_service.get_cache(cache_key)
        if result_cache:
            for index, dish in enumerate(result_cache):
                discount: Any = await self.cache_service.get_cache(f'dish:{dish.id}')
                if discount:
                    result_cache[index].price = discount
            return result_cache

        result: list[DishModel] = await self.dish_repository.get_dishes(submenu_id)
        for index, dish in enumerate(result):
            discount = await self.cache_service.get_cache(f'dish:{dish.id}')
            if discount:
                result[index].price = discount

        await self.cache_service.set_cache(cache_key=cache_key, result=result)
        return result

    async def get_dish(self, url: str, dish_id: UUID) -> DishModel:
        """
        Получить информацию о блюде по его идентификатору.

        :param url: URL запроса.
        :param dish_id: Идентификатор блюда.
        :return: Модель блюда.
        """
        result_cache: DishModel | None = await self.cache_service.get_cache(url)
        discount: Any | None = await self.cache_service.get_cache(f'dish:{dish_id}')
        if result_cache:
            if discount:
                result_cache.price = discount
            return result_cache

        result: DishModel = await self.dish_repository.get_dish(dish_id)
        if discount:
            result.price = discount
        await self.cache_service.set_cache(cache_key=url, result=result)
        return result

    async def create_dish(self, menu_id: UUID, submenu_id: UUID, dish_update: DishCreate) -> DishModel:
        """
        Создать новое блюдо в подменю.

        :param menu_id: Идентификатор меню.
        :param submenu_id: Идентификатор подменю.
        :param dish_update: Данные для создания блюда.
        :return: Модель созданного блюда.
        """
        result: DishModel = await self.dish_repository.create_dish(submenu_id, dish_update)
        self.background_tasks.add_task(
            self.cache_service.delete_cache,
            f'/api/v1/menus/{menu_id}',
            f'/api/v1/menus/{menu_id}/submenus/{submenu_id}',
            f'get_dishes:{menu_id}:{submenu_id}',
            f'get_submenus:{menu_id}',
            'get_menus'
        )
        return result

    async def update_dish(
            self,
            menu_id: UUID,
            submenu_id: UUID,
            dish_id: UUID,
            dish_update: DishUpdate
    ) -> DishModel:
        """
        Обновить информацию о блюде.

        :param menu_id: Идентификатор меню.
        :param submenu_id: Идентификатор подменю.
        :param dish_id: Идентификатор блюда, которое нужно обновить.
        :param dish_update: Схема данных для обновления информации о блюде.
        :return: Модель обновленного блюда.
        """
        result: DishModel = await self.dish_repository.update_dish(dish_id, dish_update)
        self.background_tasks.add_task(
            self.cache_service.delete_cache,
            f'get_dishes:{menu_id}:{submenu_id}',
            f'/api/v1/menus/{menu_id}/submenus/{submenu_id}/dishes/{dish_id}'
        )
        return result

    async def delete_dish(self, menu_id: UUID, submenu_id: UUID, dish_id: UUID) -> DishModel:
        """
        Удалить блюдо.

        :param menu_id: Идентификатор меню.
        :param submenu_id: Идентификатор подменю.
        :param dish_id: Идентификатор блюда, которое нужно удалить.
        :return: Модель удаленного блюда.
        """
        result: DishModel = await self.dish_repository.delete_dish(dish_id)
        self.background_tasks.add_task(
            self.cache_service.delete_related_cache,
            'dish',
            menu_id=menu_id,
            submenu_id=submenu_id,
            dish_id=dish_id
        )
        return result
