from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, \
    InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session
import keyboards as kb
from database import get_db
import onesignal_api
import logging

router = Router()
logger = logging.getLogger(__name__)


class OneSignalStates(StatesGroup):
    waiting_for_task_selection = State()


@router.message(F.text == "🌐 Web Notifications")
async def onesignal_main_menu(message: Message) -> None:
    """Главное меню OneSignal уведомлений"""
    db: Session = next(get_db())
    from database import User

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user or not user.partner_id:
        await message.answer(
            "❌ Сначала пригласите собеседника!",
            reply_markup=kb.get_main_menu_keyboard(has_partner=False)
        )
        return

    # Проверяем конфигурацию OneSignal
    if not onesignal_api.onesignal_api.is_configured:
        await message.answer(
            "🌐 <b>Web Notifications (Отключено)</b>\n\n"
            "Настройте OneSignal для отправки уведомлений!\n\n"
            "📌 <b>Требуется в .env:</b>\n"
            "ONESIGNAL_APP_ID=ваш_app_id\n"
            "ONESIGNAL_API_KEY=ваш_api_key\n\n"
            "У вас уже есть App ID и API Key?",
            parse_mode="HTML"
        )
        return

    # Тестируем подключение
    connection_test = onesignal_api.onesignal_api.test_connection()

    if not connection_test['success']:
        await message.answer(
            f"❌ <b>Ошибка подключения к OneSignal</b>\n\n"
            f"Ошибка: {connection_test.get('error', 'Неизвестная ошибка')}\n\n"
            f"Проверьте:\n"
            f"1. Правильность ключей в .env\n"
            f"2. Активность аккаунта OneSignal\n"
            f"3. Наличие подписчиков в приложении",
            parse_mode="HTML"
        )
        return

    # Получаем статистику
    stats = onesignal_api.onesignal_api.get_app_stats()

    stats_text = ""
    if stats['success']:
        stats_text = (
            f"📊 <b>Статистика OneSignal:</b>\n"
            f"• Приложение: {stats.get('app_name', 'N/A')}\n"
            f"• Всего пользователей: {stats.get('players', 0)}\n"
            f"• Активных: {stats.get('messageable_players', 0)}\n\n"
        )

    await message.answer(
        f"🌐 <b>Web Notifications (OneSignal)</b>\n\n"
        f"{stats_text}"
        f"📌 <b>Функции:</b>\n"
        f"• 🔔 Тестовое уведомление\n"
        f"• 📝 Напомнить о задаче (Web)\n"
        f"• ⚙️ Настройки и статус\n"
        f"• 📊 Статистика\n\n"
        f"Уведомления отправляются на все устройства с подпиской.",
        parse_mode="HTML",
        reply_markup=kb.get_onesignal_menu_keyboard()
    )


@router.message(F.text == "🔔 Тест OneSignal")
async def send_test_onesignal(message: Message) -> None:
    """Отправить тестовое уведомление через OneSignal"""
    await message.answer("🌐 Отправляю тестовое уведомление через OneSignal...")

    result = onesignal_api.onesignal_api.send_notification(
        contents={"ru": "✅ OneSignal API работает! Тест от TaskBuddy Bot."},
        headings={"ru": "🎉 OneSignal подключен"},
        included_segments=["All"],
        data={"test": True, "source": "telegram_bot"}
    )

    if result['success']:
        await message.answer(
            f"✅ <b>Тестовое уведомление отправлено!</b>\n\n"
            f"🌐 Сервис: {result.get('service', 'OneSignal')}\n"
            f"📨 Статус: Успешно отправлено\n\n"
            f"<i>Проверьте OneSignal Dashboard для просмотра статистики</i>",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ <b>Ошибка отправки</b>\n\n"
            f"Ошибка: {result.get('error', 'Неизвестная ошибка')}\n\n"
            f"Проверьте настройки OneSignal.",
            parse_mode="HTML"
        )


@router.message(F.text == "📝 Web напоминание")
async def send_web_reminder_menu(message: Message) -> None:
    """Меню для отправки web-напоминаний о задачах"""
    db: Session = next(get_db())
    from database import User, Task

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user or not user.partner_id:
        await message.answer("❌ Сначала пригласите собеседника!")
        return

    # Получаем активные задачи пользователя
    tasks = db.query(Task).filter(
        Task.assigned_by_id == user.id,
        Task.completed == False
    ).all()

    if not tasks:
        await message.answer("📭 У вас нет активных задач для напоминания")
        return

    # Создаем клавиатуру с задачами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for task in tasks[:5]:  # Ограничиваем 5 задачами
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"📌 {task.title[:20]}...",
                callback_data=f"onesignal_task:{task.id}"
            )
        ])

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_onesignal")
    ])

    await message.answer(
        f"🌐 <b>Выберите задачу для Web-напоминания</b>\n\n"
        f"📋 Найдено задач: {len(tasks)}\n\n"
        f"⚠️ <b>Внимание:</b>\n"
        f"Web-напоминания отправятся всем подписчикам OneSignal.",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("onesignal_task:"))
async def send_onesignal_task_reminder(callback: CallbackQuery) -> None:
    """Отправить OneSignal напоминание о задаче"""
    task_id = int(callback.data.split(":")[1])

    db: Session = next(get_db())
    from database import Task, User

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        await callback.message.answer("❌ Задача не найдена")
        await callback.answer()
        return

    user = db.query(User).filter(User.id == task.assigned_by_id).first()

    await callback.message.answer(f"🌐 Отправляю Web-напоминание о задаче: {task.title}")

    # Отправляем через OneSignal
    result = onesignal_api.onesignal_api.send_task_notification(
        task_title=task.title,
        from_user=user.full_name if user else "Неизвестный",
        task_description=task.description,
        task_id=task.id
    )

    if result['success']:
        await callback.message.answer(
            f"✅ <b>Web-напоминание отправлено!</b>\n\n"
            f"📌 Задача: {task.title}\n"
            f"🌐 Сервис: OneSignal\n"
            f"📨 Статус: Успешно отправлено\n\n"
            f"<i>Уведомление отправлено всем подписчикам</i>",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            f"❌ <b>Ошибка отправки</b>\n\n"
            f"Ошибка: {result.get('error', 'Неизвестная ошибка')}",
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data == "cancel_onesignal")
async def cancel_onesignal(callback: CallbackQuery) -> None:
    """Отмена OneSignal действия"""
    await callback.message.answer("❌ Действие отменено")
    await callback.answer()


@router.message(F.text == "📊 Статистика API")
async def show_api_stats(message: Message) -> None:
    """Показать статистику OneSignal API"""
    if not onesignal_api.onesignal_api.is_configured:
        await message.answer("❌ OneSignal не настроен")
        return

    await message.answer("📊 Запрашиваю статистику OneSignal...")

    # Получаем статистику приложения
    stats = onesignal_api.onesignal_api.get_app_stats()

    if stats['success']:
        stats_text = (
            f"📈 <b>OneSignal Статистика</b>\n\n"
            f"🏷️ <b>Приложение:</b> {stats.get('app_name', 'N/A')}\n"
            f"👥 <b>Всего пользователей:</b> {stats.get('players', 0)}\n"
            f"✅ <b>Активных:</b> {stats.get('messageable_players', 0)}\n"
            f"📅 <b>Создано:</b> {stats.get('created_at', 'N/A')[:10]}\n\n"
        )

        stats_text += "<i>Для детальной статистики посетите OneSignal Dashboard</i>"

        await message.answer(stats_text, parse_mode="HTML")
    else:
        await message.answer(
            f"❌ <b>Ошибка получения статистики</b>\n\n"
            f"{stats.get('error', 'Неизвестная ошибка')}",
            parse_mode="HTML"
        )


@router.message(F.text == "⚙️ Настройки")
async def onesignal_settings(message: Message) -> None:
    """Настройки OneSignal"""
    if not onesignal_api.onesignal_api.is_configured:
        config_status = "❌ Не настроено"
        config_details = "Добавьте ключи в .env файл"
    else:
        config_status = "✅ Настроено"
        config_details = f"App ID: {onesignal_api.onesignal_api.app_id[:8]}..."

    await message.answer(
        f"⚙️ <b>Настройки OneSignal</b>\n\n"
        f"🔧 <b>Статус:</b> {config_status}\n"
        f"📝 <b>Детали:</b> {config_details}\n\n"
        f"📌 <b>Ключи API:</b>\n"
        f"• ONESIGNAL_APP_ID\n"
        f"• ONESIGNAL_API_KEY\n\n"
        f"🌐 <b>Dashboard:</b>\n"
        f"https://onesignal.com/apps/{onesignal_api.onesignal_api.app_id}\n\n"
        f"📚 <b>Документация:</b>\n"
        f"https://documentation.onesignal.com/",
        parse_mode="HTML",
        disable_web_page_preview=True
    )


@router.message(Command("onesignal_test"))
async def onesignal_test_command(message: Message) -> None:
    """Команда для быстрого теста OneSignal"""
    await send_test_onesignal(message)


@router.message(Command("send_notification"))
async def send_notification_command(message: Message) -> None:
    """Команда для отправки кастомного уведомления"""
    args = message.text.split(maxsplit=2)

    if len(args) < 3:
        await message.answer(
            "Использование: /send_notification <заголовок> <сообщение>\n"
            "Пример: /send_notification Важное \"Проверьте задачи\""
        )
        return

    title = args[1]
    notification_message = args[2]

    await message.answer(f"🌐 Отправляю OneSignal уведомление: {title}")

    result = onesignal_api.onesignal_api.send_notification(
        contents={"ru": notification_message},
        headings={"ru": title},
        included_segments=["All"]
    )

    if result['success']:
        await message.answer(f"✅ Уведомление отправлено!")
    else:
        await message.answer(f"❌ Ошибка: {result.get('error')}")