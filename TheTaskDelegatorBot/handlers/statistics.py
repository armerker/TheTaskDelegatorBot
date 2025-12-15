from aiogram import Router, F
from aiogram.types import Message
from database import get_db
import keyboards as kb

router = Router()


@router.message(F.text == "📊 Статистика")
async def get_user_statistics(message: Message) -> None:
    """Отображает статистику пользователя"""
    db = next(get_db())
    from database import User, Task

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user or not user.partner_id:
        await message.answer(
            "❌ У вас нет собеседника!\n\nНайдите собеседника чтобы просматривать статистику.",
            reply_markup=kb.get_main_menu_keyboard(has_partner=False)
        )
        return

    # Получаем статистику собеседника
    partner = db.query(User).filter(User.id == user.partner_id).first()
    if not partner:
        await message.answer("❌ Ошибка: собеседник не найден")
        return


    user_created: int = getattr(user, 'tasks_created_count', 0)
    user_completed: int = getattr(user, 'tasks_completed_count', 0)
    user_received: int = getattr(user, 'tasks_received_count', 0)
    user_deleted: int = getattr(user, 'tasks_deleted_count', 0)

    partner_created: int = getattr(partner, 'tasks_created_count', 0)
    partner_completed: int = getattr(partner, 'tasks_completed_count', 0)
    partner_received: int = getattr(partner, 'tasks_received_count', 0)
    partner_deleted: int = getattr(partner, 'tasks_deleted_count', 0)

    completed_tasks: int = db.query(Task).filter(
        Task.assigned_to_id == user.id,
        Task.completed == True
    ).count()

    pending_tasks: int = db.query(Task).filter(
        Task.assigned_to_id == user.id,
        Task.completed == False
    ).count()

    # Расчет процента выполнения
    completion_rate: float = 0
    if user_received > 0:
        completion_rate = (user_completed / user_received) * 100

    # Статистика пользователя
    stats_text: str = f"📊 <b>ВАША СТАТИСТИКА</b>\n\n"
    stats_text += f"👤 <b>Пользователь:</b> {user.full_name or 'Аноним'}\n\n"

    stats_text += f"📈 <b>МОЯ СТАТИСТИКА:</b>\n"
    stats_text += f"• Создал задач: <b>{user_created}</b>\n"
    stats_text += f"• Выполнил задач: <b>{user_completed}</b>\n"
    stats_text += f"• Получил задач: <b>{user_received}</b>\n"
    stats_text += f"• Удалил задач: <b>{user_deleted}</b>\n"
    stats_text += f"• Процент выполнения: <b>{completion_rate:.1f}%</b>\n"
    stats_text += f"• Задач в ожидании: <b>{pending_tasks}</b>\n\n"

    # Статистика собеседника
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

    stats_text += f"📊 <b>ОБЩАЯ СТАТИСТИКА:</b>\n"
    stats_text += f"• Всего создано задач: <b>{total_tasks_created}</b>\n"
    stats_text += f"• Всего выполнено задач: <b>{total_tasks_completed}</b>\n"
    stats_text += f"• Общий процент выполнения: <b>{total_completion_rate:.1f}%</b>"

    await message.answer(stats_text, parse_mode="HTML")