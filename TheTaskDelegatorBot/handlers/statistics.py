from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_db
import keyboards as kb
import utils
from datetime import datetime, timedelta

router = Router()


@router.message(F.text == "📊 Статистика")
async def get_user_statistics(message: Message) -> None:
    """Отображает статистику пользователя"""
    db = next(get_db())
    from database import User, Task

    # Обновляем активность пользователя
    utils.update_user_activity(db, message.from_user.id)

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user:
        await message.answer("❌ Пользователь не найден")
        return

    if not user.partner_id:
        # Показываем общую статистику если нет партнера
        await show_general_stats(message, db, user)
        return

    partner = db.query(User).filter(User.id == user.partner_id).first()
    if not partner:
        await message.answer("❌ Ошибка: собеседник не найден")
        return

    # Статистика пользователя
    user_created: int = getattr(user, 'tasks_created_count', 0)
    user_completed: int = getattr(user, 'tasks_completed_count', 0)
    user_received: int = getattr(user, 'tasks_received_count', 0)
    user_deleted: int = getattr(user, 'tasks_deleted_count', 0)
    user_onesignal_sent: int = getattr(user, 'onesignal_notifications_sent', 0)
    user_total_messages: int = getattr(user, 'total_messages_count', 0)

    # Активность пользователя
    days_since_joined = (datetime.utcnow() - user.joined_date).days if user.joined_date else 0
    days_since_active = (datetime.utcnow() - user.last_active_date).days if user.last_active_date else 0

    # Статистика партнера
    partner_created: int = getattr(partner, 'tasks_created_count', 0)
    partner_completed: int = getattr(partner, 'tasks_completed_count', 0)
    partner_received: int = getattr(partner, 'tasks_received_count', 0)
    partner_deleted: int = getattr(partner, 'tasks_deleted_count', 0)

    pending_tasks: int = db.query(Task).filter(
        Task.assigned_to_id == user.id,
        Task.completed == False
    ).count()

    completion_rate: float = 0
    if user_received > 0:
        completion_rate = (user_completed / user_received) * 100

    stats_text: str = f"📊 <b>ВАША СТАТИСТИКА</b>\n\n"
    stats_text += f"👤 <b>Пользователь:</b> {user.full_name or 'Аноним'}\n"
    stats_text += f"📅 <b>В боте:</b> {days_since_joined} дней\n"
    stats_text += f"🔄 <b>Активен:</b> {days_since_active} дней назад\n"
    stats_text += f"💬 <b>Сообщений:</b> {user_total_messages}\n"
    stats_text += f"🌐 <b>OneSignal отправлено:</b> {user_onesignal_sent}\n\n"

    stats_text += f"📈 <b>МОЯ СТАТИСТИКА:</b>\n"
    stats_text += f"• Создал задач: <b>{user_created}</b>\n"
    stats_text += f"• Выполнил задач: <b>{user_completed}</b>\n"
    stats_text += f"• Получил задач: <b>{user_received}</b>\n"
    stats_text += f"• Удалил задач: <b>{user_deleted}</b>\n"
    stats_text += f"• Процент выполнения: <b>{completion_rate:.1f}%</b>\n"
    stats_text += f"• Задач в ожидании: <b>{pending_tasks}</b>\n\n"

    partner_completion_rate: float = 0
    if partner_received > 0:
        partner_completion_rate = (partner_completed / partner_received) * 100

    stats_text += f"🤝 <b>СТАТИСТИКА СОБЕСЕДНИКА ({partner.full_name or 'Аноним'}):</b>\n"
    stats_text += f"• Создал задач: <b>{partner_created}</b>\n"
    stats_text += f"• Выполнил задач: <b>{partner_completed}</b>\n"
    stats_text += f"• Получил задач: <b>{partner_received}</b>\n"
    stats_text += f"• Удалил задач: <b>{partner_deleted}</b>\n"
    stats_text += f"• Процент выполнения: <b>{partner_completion_rate:.1f}%</b>\n\n"

    total_tasks_created: int = user_created + partner_created
    total_tasks_completed: int = user_completed + partner_completed
    total_completion_rate: float = 0
    if (user_received + partner_received) > 0:
        total_completion_rate = (total_tasks_completed / (user_received + partner_received)) * 100

    stats_text += f"📊 <b>ОБЩАЯ СТАТИСТИКА ПАРЫ:</b>\n"
    stats_text += f"• Всего создано задач: <b>{total_tasks_created}</b>\n"
    stats_text += f"• Всего выполнено задач: <b>{total_tasks_completed}</b>\n"
    stats_text += f"• Общий процент выполнения: <b>{total_completion_rate:.1f}%</b>"

    # Клавиатура для переключения между статистиками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📈 Общая статистика", callback_data="show_general_stats"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_stats")
        ]
    ])

    await message.answer(stats_text, parse_mode="HTML", reply_markup=keyboard)


async def show_general_stats(message: Message, db, user=None) -> None:
    """Показать общую статистику приложения"""
    # Получаем сводную статистику
    app_stats = utils.get_app_stats_summary(db)

    stats_text = f"📊 <b>ОБЩАЯ СТАТИСТИКА ПРИЛОЖЕНИЯ</b>\n\n"

    # Статистика пользователей
    stats_text += f"👥 <b>ПОЛЬЗОВАТЕЛИ:</b>\n"
    stats_text += f"• Всего пользователей: <b>{app_stats['total_users']}</b>\n"
    stats_text += f"• Активных (7 дней): <b>{app_stats['active_users']}</b>\n"
    stats_text += f"• С собеседниками: <b>{app_stats['users_with_partner']}</b>\n"
    stats_text += f"• Парность: <b>{app_stats['partner_rate']:.1f}%</b>\n\n"

    # Статистика задач
    stats_text += f"📋 <b>ЗАДАЧИ:</b>\n"
    stats_text += f"• Всего создано: <b>{app_stats['total_tasks']}</b>\n"
    stats_text += f"• Выполнено: <b>{app_stats['completed_tasks']}</b>\n"
    stats_text += f"• Активных: <b>{app_stats['active_tasks']}</b>\n"
    stats_text += f"• Процент выполнения: <b>{app_stats['completion_rate']:.1f}%</b>\n\n"

    # Статистика API
    stats_text += f"🌐 <b>ВНЕШНИЕ API:</b>\n"
    stats_text += f"• OneSignal уведомлений: <b>{app_stats['onesignal_notifications_total']}</b>\n\n"

    if user:
        # Личная статистика если пользователь есть
        user_tasks_created = getattr(user, 'tasks_created_count', 0)
        user_tasks_completed = getattr(user, 'tasks_completed_count', 0)
        user_days_in_app = (datetime.utcnow() - user.joined_date).days if user.joined_date else 0

        stats_text += f"👤 <b>ВАША СТАТИСТИКА:</b>\n"
        stats_text += f"• Вы в боте: <b>{user_days_in_app}</b> дней\n"
        stats_text += f"• Ваш вклад в задачи: <b>{user_tasks_created}</b> создано, <b>{user_tasks_completed}</b> выполнено\n"

        if app_stats['total_tasks'] > 0:
            user_contribution = ((user_tasks_created + user_tasks_completed) / (app_stats['total_tasks'] * 2)) * 100
            stats_text += f"• Ваш вклад: <b>{user_contribution:.1f}%</b> от всех задач\n"

    stats_text += f"\n📅 <i>Обновлено: {app_stats['updated_at'].strftime('%d.%m.%Y %H:%M') if app_stats['updated_at'] else 'Нет данных'}</i>"

    # Клавиатура
    keyboard = None
    if user and user.partner_id:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Моя статистика", callback_data="show_my_stats"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_general_stats")
            ]
        ])

    await message.answer(stats_text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data == "show_general_stats")
async def show_general_stats_callback(callback: CallbackQuery) -> None:
    """Показать общую статистику по callback"""
    db = next(get_db())
    from database import User

    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
    await show_general_stats(callback.message, db, user)
    await callback.answer()


@router.callback_query(F.data == "show_my_stats")
async def show_my_stats_callback(callback: CallbackQuery) -> None:
    """Показать мою статистику по callback"""
    await get_user_statistics(callback.message)
    await callback.answer()


@router.callback_query(F.data == "refresh_stats")
async def refresh_stats_callback(callback: CallbackQuery) -> None:
    """Обновить статистику"""
    await get_user_statistics(callback.message)
    await callback.answer("✅ Статистика обновлена")


@router.callback_query(F.data == "refresh_general_stats")
async def refresh_general_stats_callback(callback: CallbackQuery) -> None:
    """Обновить общую статистику"""
    db = next(get_db())
    from database import User

    utils.update_app_stats(db)  # Принудительно обновляем статистику
    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
    await show_general_stats(callback.message, db, user)
    await callback.answer("✅ Статистика обновлена")