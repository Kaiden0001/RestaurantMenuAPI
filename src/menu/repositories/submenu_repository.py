from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Delete, Result, Select, Update, delete, func, select, update

from src.menu.models.dish_model import Dish
from src.menu.models.submenu_model import Submenu, SubmenuDetailModel, SubmenuModel
from src.menu.repositories.base_repository import BaseRepository
from src.menu.schemas.submenu_schema import SubmenuCreate, SubmenuUpdate


class SubmenuRepository(BaseRepository):

    async def _get_submenu_query(self, menu_id: UUID, submenu_id: UUID | None = None) -> Result:
        """
        Возвращает запрос для получения подробной информации о подменю или всех подменю для конкретного меню.

        :param menu_id: Уникальный идентификатор меню.
        :param submenu_id: (Опционально) Уникальный идентификатор подменю.
        :return: Результат выполнения запроса SQLAlchemy.
        """
        submenu_query: Select = select(
            Submenu.id,
            Submenu.title,
            Submenu.description,
            func.count(Dish.id).label('dish_count')
        ).select_from(Submenu).outerjoin(Dish, Submenu.id == Dish.submenu_id)

        if submenu_id:
            submenu_query = submenu_query.filter(
                Submenu.menu_id == menu_id, Submenu.id == submenu_id).group_by(Submenu.id)
        else:
            submenu_query = submenu_query.filter(Submenu.menu_id == menu_id).group_by(Submenu.id)

        return await self.session.execute(submenu_query)

    @staticmethod
    def _create_submenu_detail_model(submenu: Any, menu_id: UUID) -> SubmenuDetailModel:
        """
        Создает модель данных SubmenuDetailModel на основе результата запроса к подменю.

        :param submenu: Результат запроса к подменю.
        :param menu_id: Уникальный идентификатор меню.
        :return: Модель данных SubmenuDetailModel.
        """
        return SubmenuDetailModel(
            id=submenu.id,
            title=submenu.title,
            menu_id=menu_id,
            description=submenu.description,
            dishes_count=int(submenu.dish_count) if submenu.dish_count is not None else 0
        )

    async def get_submenus(self, menu_id: UUID) -> list[SubmenuDetailModel]:
        """
        Получение списка подменю для конкретного меню.

        :param menu_id: Уникальный идентификатор меню, для которого нужно
        получить подменю.
        :return: Список моделей данных SubmenuModel.
        """
        result_submenus: Result = await self._get_submenu_query(menu_id)
        submenus: list[SubmenuDetailModel] = []

        for submenu in result_submenus:
            submenu_detail: SubmenuDetailModel = self._create_submenu_detail_model(submenu, menu_id)
            submenus.append(submenu_detail)
        return submenus

    async def create_submenu(self, menu_id: UUID, submenu_create: SubmenuCreate) -> SubmenuModel:
        """
        Создание нового подменю.

        :param menu_id: Уникальный идентификатор меню, к которому привязывается
         подменю.
        :param submenu_create: Схема данных для создания нового подменю.
        :return: Модель данных созданного подменю.
        """
        db_submenu: Submenu = Submenu(menu_id=menu_id, **submenu_create.model_dump())
        self.session.add(db_submenu)
        await self.session.commit()
        await self.session.refresh(db_submenu)

        return db_submenu

    async def get_submenu_detail(self, menu_id: UUID, submenu_id: UUID) -> SubmenuDetailModel:
        """
        Получение подробной информации о конкретном подменю.

        :param menu_id: Уникальный идентификатор меню, к которому привязано
        подменю.
        :param submenu_id: Уникальный идентификатор подменю (UUID).
        :return: Модель данных SubmenuDetailModel.
        :raise HTTPException: Исключение с кодом 404, если подменю не найдено.
        """
        result_submenu: Result = await self._get_submenu_query(menu_id, submenu_id)
        submenu: Any = result_submenu.first()

        if not submenu:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='submenu not found')

        submenu_detail: SubmenuDetailModel = self._create_submenu_detail_model(submenu, menu_id)

        return submenu_detail

    async def update_submenu(self, menu_id: UUID, submenu_id: UUID, submenu_update: SubmenuUpdate) -> SubmenuModel:
        """
        Обновление информации о подменю.

        :param menu_id: Уникальный идентификатор меню, к которому привязано подменю.
        :param submenu_id: Уникальный идентификатор подменю, которое нужно обновить.
        :param submenu_update: Схема данных для обновления информации о подменю.
        :return: Модель обновленного подменю.
        :raise HTTPException: Исключение с кодом 404, если подменю не найдено.
        """
        existing_submenu: Any = await self.get_submenu_by_id(submenu_id)
        if not existing_submenu:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='submenu not found')

        query: Update = update(Submenu).where(Submenu.menu_id == menu_id,
                                              Submenu.id == submenu_id).values(**submenu_update.model_dump())
        await self.session.execute(query)
        await self.session.commit()

        return await self.get_submenu_by_id(submenu_id)

    async def delete_submenu(self, menu_id: UUID, submenu_id: UUID) -> SubmenuModel:
        """
        Удаление подменю.

        :param menu_id: Уникальный идентификатор меню, к которому привязано подменю.
        :param submenu_id: Уникальный идентификатор подменю (UUID).
        :return: Модель данных удаленного подменю.
        :raise HTTPException: Исключение с кодом 404, если подменю не найдено.
        """
        existing_submenu: SubmenuModel = await self.get_submenu_by_id(submenu_id)

        if not existing_submenu:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='submenu not found')

        query: Delete = delete(Submenu).where(Submenu.menu_id == menu_id, Submenu.id == submenu_id)
        await self.session.execute(query)
        await self.session.commit()

        return existing_submenu
