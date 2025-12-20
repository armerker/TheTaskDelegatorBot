import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
import config
from database import init_db
from handlers import main_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    try:
        # Инициализация базы данных
        init_db()

        # Инициализация бота
        bot = Bot(token=config.config.BOT_TOKEN, parse_mode=ParseMode.HTML)

        # Инициализация диспетчера
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        dp.include_router(main_router)

        logger.info("✅ Бот запущен и готов к работе!")
        logger.info("✅ База данных инициализирована")
        logger.info("✅ Графики статистики активированы")
        logger.info("✅ Доступные модули: статистика, задачи, уведомления, графики")

        # Запуск бота
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())