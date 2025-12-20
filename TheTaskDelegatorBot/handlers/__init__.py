from aiogram import Router

# Создаем главный роутер
main_router = Router()

# Импортируем все обработчики
from .main_menu import router as main_menu_router
from .tasks import router as tasks_router
from .invite import router as invite_router
from .common import router as common_router
from .statistics import router as statistics_router
from .onesignal_handler import router as onesignal_router

# Включаем подроутеры
main_router.include_router(main_menu_router)
main_router.include_router(tasks_router)
main_router.include_router(invite_router)
main_router.include_router(common_router)
main_router.include_router(statistics_router)
main_router.include_router(onesignal_router)  # НОВЫЙ РОУТЕР