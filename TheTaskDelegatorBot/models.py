from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TaskModel:
    """Модель задачи"""
    id: int
    title: str
    description: Optional[str]
    created_at: datetime
    completed: bool
    assigned_by_id: int
    assigned_to_id: int

    @property
    def status(self) -> str:
        """Возвращает статус задачи"""
        return "✅ Выполнено" if self.completed else "⏳ Ожидает"


@dataclass
class UserModel:
    """Модель пользователя"""
    id: int
    telegram_id: int
    username: Optional[str]
    full_name: str
    partner_id: Optional[int]