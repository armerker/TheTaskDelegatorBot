import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
import config
from database import init_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 🔧 Глобальные переменные для доступа из других модулей
bot_instance = None
dp = None


async def main() -> None:
    global bot_instance, dp

    print("🚀 Запуск бота TaskBuddy...")

    # Проверяем зависимости
    try:
        import requests
        print("✅ requests установлен")
    except ImportError:
        print("❌ Библиотека 'requests' не установлена!")
        print("Установите: pip install requests")
        return

    print("📊 Инициализация базы данных...")
    init_db()
    print("✅ База данных готова")

    try:
        bot_instance = Bot(token=config.config.BOT_TOKEN, parse_mode=ParseMode.HTML)
        print(f"✅ Бот создан. ID: {bot_instance.id}")
    except Exception as e:
        print(f"❌ Ошибка создания бота: {e}")
        print(f"Проверьте токен в .env файле")
        return

    dp = Dispatcher(storage=MemoryStorage())

    # Импортируем главный роутер
    try:
        from handlers import main_router
        dp.include_router(main_router)
        print("✅ Все роутеры подключены")
    except ImportError as e:
        print(f"❌ Ошибка импорта роутеров: {e}")
        return

    print("🌐 OneSignal API: ВКЛЮЧЕНО")

    await bot_instance.delete_webhook(drop_pending_updates=True)
    print("🤖 Бот запущен! Отправьте /start")
    print("🔗 OneSignal App ID:", config.config.ONESIGNAL_APP_ID)
    print("🔗 Бот ID:", bot_instance.id)

    await dp.start_polling(bot_instance)


def get_bot():
    """Получить экземпляр бота из любого места"""
    return bot_instance


def get_dispatcher():
    """Получить диспетчер из любого места"""
    return dp


if __name__ == "__main__":
    asyncio.run(main())