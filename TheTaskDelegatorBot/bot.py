import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
import config
from database import init_db

logging.basicConfig(level=logging.INFO)

bot_instance = None


async def main() -> None:
    global bot_instance

    print("🚀 Запуск бота...")

    print("📊 Инициализация базы данных...")
    init_db()
    print("✅ База данных готова")

    bot_instance = Bot(token=config.config.BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())

    # Импортируем главный роутер
    from handlers import main_router

    dp.include_router(main_router)

    print("✅ Все роутеры подключены")

    await bot_instance.delete_webhook(drop_pending_updates=True)
    print("🤖 Бот запущен! Отправьте /start")

    await dp.start_polling(bot_instance)


if __name__ == "__main__":
    asyncio.run(main())