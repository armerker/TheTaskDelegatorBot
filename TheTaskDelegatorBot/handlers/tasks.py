from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session
import keyboards as kb
import utils
from database import get_db
from datetime import datetime

router = Router()


class TaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()


async def send_notification(user_id: int, text: str):
    """Отправляет уведомление пользователю"""
    try:
        from bot import bot_instance as bot
        result = await bot.send_message(user_id, text, parse_mode="HTML")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления пользователю {user_id}: {type(e).__name__}: {e}")
        return False


# === СОЗДАНИЕ ЗАДАЧИ ===

@router.message(F.text == "📝 Создать задание")
async def create_task_start(message: Message, state: FSMContext):
    """Начать создание задачи"""
    db = next(get_db())
    from database import User

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user or not user.partner_id:
        await message.answer(
            "❌ Сначала пригласите собеседника!",
            reply_markup=kb.get_main_menu_keyboard(has_partner=False)
        )
        return

    await state.set_state(TaskStates.waiting_for_title)
    await message.answer(
        "📝 Введите название задачи:",
        reply_markup=kb.get_cancel_keyboard()
    )


@router.message(TaskStates.waiting_for_title)
async def process_task_title(message: Message, state: FSMContext):
    """Обработать название задачи"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Создание задачи отменено",
            reply_markup=kb.get_main_menu_keyboard(has_partner=True)
        )
        return

    if len(message.text) < 3:
        await message.answer("❌ Название должно быть не менее 3 символов")
        return

    await state.update_data(title=message.text)
    await state.set_state(TaskStates.waiting_for_description)

    await message.answer(
        "📄 Введите описание задачи (или нажмите 'Пропустить'):",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⏭️ Пропустить")],
                [KeyboardButton(text="❌ Отмена")]
            ],
            resize_keyboard=True
        )
    )


@router.message(TaskStates.waiting_for_description)
async def process_task_description(message: Message, state: FSMContext):
    """Обработать описание задачи"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Создание задачи отменено",
            reply_markup=kb.get_main_menu_keyboard(has_partner=True)
        )
        return

    data = await state.get_data()
    description = None if message.text == "⏭️ Пропустить" else message.text

    db = next(get_db())
    from database import User, Task

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    partner = db.query(User).filter(User.id == user.partner_id).first()

    if not partner:
        await message.answer("❌ Ошибка: собеседник не найден")
        await state.clear()
        return

    # Создаем задачу
    task = Task(
        title=data['title'],
        description=description,
        assigned_by_id=user.id,
        assigned_to_id=partner.id,
        created_at=datetime.utcnow()
    )

    db.add(task)

    # УВЕЛИЧИВАЕМ СТАТИСТИКУ
    try:
        user.tasks_created_count += 1
        partner.tasks_received_count += 1
    except:
        # Если колонки еще не существуют, игнорируем
        pass

    db.commit()
    await state.clear()

    # Формируем уведомление для собеседника
    user_name = message.from_user.full_name or f"@{message.from_user.username}" if message.from_user.username else "Собеседник"

    notification_text = (
        f"📬 <b>НОВАЯ ЗАДАЧА!</b>\n\n"
        f"<b>{user_name}</b> назначил(а) вам задачу:\n\n"
        f"📌 <b>{data['title']}</b>\n"
    )

    if description:
        notification_text += f"📝 {description}\n"

    notification_text += f"\n⏰ {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}"

    # Отправляем уведомление собеседнику
    await send_notification(partner.telegram_id, notification_text)

    # ✅ СООБЩЕНИЕ СОЗДАТЕЛЮ о создании задачи
    creation_message = f"✅ Задача <b>'{data['title']}'</b> создана и отправлена собеседнику!"
    if description:
        creation_message += f"\n📝 Описание: {description}"

    await message.answer(creation_message, parse_mode="HTML")

    # Возвращаем в главное меню
    await message.answer(
        "Выберите действие:",
        reply_markup=kb.get_main_menu_keyboard(has_partner=True)
    )


# === УДАЛЕНИЕ ЗАДАЧИ ===

@router.message(F.text == "🗑️ Удалить задачу")
async def delete_task_menu(message: Message):
    """Показать меню удаления задач"""
    db = next(get_db())
    from database import User, Task

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user or not user.partner_id:
        await message.answer(
            "❌ Сначала пригласите собеседника!",
            reply_markup=kb.get_main_menu_keyboard(has_partner=False)
        )
        return

    # ПОКАЗЫВАЕМ ТОЛЬКО НЕВЫПОЛНЕННЫЕ ЗАДАЧИ
    tasks = db.query(Task).filter(
        Task.assigned_by_id == user.id,
        Task.completed == False
    ).all()

    if not tasks:
        await message.answer("📭 У вас нет активных задач для удаления")
        return

    await message.answer(
        "🗑️ Выберите задачу для удаления:",
        reply_markup=kb.get_tasks_keyboard(tasks, "delete_task")
    )


@router.callback_query(F.data.startswith("delete_task:"))
async def delete_task_callback(callback: CallbackQuery):
    """Удалить задачу"""
    task_id = int(callback.data.split(":")[1])

    db = next(get_db())
    from database import Task, User

    task = db.query(Task).filter(Task.id == task_id).first()

    if task:
        task_title = task.title

        # Получаем информацию о собеседнике
        partner = db.query(User).filter(User.id == task.assigned_to_id).first()

        # Удаляем задачу
        db.delete(task)

        # УВЕЛИЧИВАЕМ СТАТИСТИКУ УДАЛЕНИЯ
        try:
            creator = db.query(User).filter(User.id == task.assigned_by_id).first()
            if creator:
                creator.tasks_deleted_count += 1
        except:
            pass

        db.commit()

        # Уведомляем собеседника об удалении задачи
        if partner:
            user_name = callback.from_user.full_name or f"@{callback.from_user.username}" if callback.from_user.username else "Собеседник"

            delete_notification = (
                f"🗑️ <b>ЗАДАЧА УДАЛЕНА</b>\n\n"
                f"<b>{user_name}</b> удалил(а) задачу:\n"
                f"📌 {task_title}"
            )

            await send_notification(partner.telegram_id, delete_notification)

        # ✅ СООБЩЕНИЕ ОБ УДАЛЕНИИ
        await callback.message.answer(
            f"🗑️ Задача <b>'{task_title}'</b> удалена!",
            parse_mode="HTML"
        )

        # Возвращаем в меню
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=kb.get_main_menu_keyboard(has_partner=True)
        )
    else:
        await callback.message.answer("❌ Задача не найдена!")

    await callback.answer()


# === ВЫПОЛНЕНИЕ ЗАДАЧИ ===

@router.message(F.text == "✅ Выполнил задачу")
async def complete_task_menu(message: Message):
    """Показать меню выполнения задач"""
    db = next(get_db())
    from database import User, Task

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user or not user.partner_id:
        await message.answer(
            "❌ Сначала пригласите собеседника!",
            reply_markup=kb.get_main_menu_keyboard(has_partner=False)
        )
        return

    # ПОКАЗЫВАЕМ ТОЛЬКО НЕВЫПОЛНЕННЫЕ ЗАДАЧИ
    tasks = db.query(Task).filter(
        Task.assigned_to_id == user.id,
        Task.completed == False
    ).all()

    if not tasks:
        await message.answer("📭 У вас нет задач для выполнения")
        return

    await message.answer(
        "✅ Выберите выполненную задачу:",
        reply_markup=kb.get_tasks_keyboard(tasks, "complete_task")
    )


@router.callback_query(F.data.startswith("complete_task:"))
async def complete_task_callback(callback: CallbackQuery):
    """Отметить задачу как выполненную"""
    task_id = int(callback.data.split(":")[1])

    db = next(get_db())
    from database import Task, User

    task = db.query(Task).filter(Task.id == task_id).first()

    if task:
        task_title = task.title
        task.completed = True
        task.completed_at = datetime.utcnow()

        # Получаем информацию о создателе задачи
        creator = db.query(User).filter(User.id == task.assigned_by_id).first()

        # УВЕЛИЧИВАЕМ СТАТИСТИКУ ВЫПОЛНЕНИЯ
        try:
            executor = db.query(User).filter(User.id == task.assigned_to_id).first()
            if executor:
                executor.tasks_completed_count += 1
        except:
            pass

        db.commit()

        # Уведомляем создателя задачи о выполнении
        if creator:
            user_name = callback.from_user.full_name or f"@{callback.from_user.username}" if callback.from_user.username else "Собеседник"

            completion_notification = (
                f"✅ <b>ЗАДАЧА ВЫПОЛНЕНА!</b>\n\n"
                f"<b>{user_name}</b> выполнил(а) вашу задачу:\n\n"
                f"📌 <b>{task_title}</b>\n"
                f"⏰ Время: {task.completed_at.strftime('%d.%m.%Y %H:%M')}"
            )

            await send_notification(creator.telegram_id, completion_notification)

        # ✅ СООБЩЕНИЕ О ВЫПОЛНЕНИИ
        await callback.message.answer(
            f"✅ Задача <b>'{task_title}'</b> выполнена!\n"
            f"⏰ {task.completed_at.strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML"
        )

        # Возвращаем в меню
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=kb.get_main_menu_keyboard(has_partner=True)
        )
    else:
        await callback.message.answer("❌ Задача не найдена!")

    await callback.answer()


# === ПРОСМОТР ЗАДАЧ ===

@router.message(F.text == "📋 Мои задачи")
async def view_tasks(message: Message):
    """Показать все задачи"""
    db = next(get_db())
    from database import User, Task

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user:
        await message.answer("❌ Пользователь не найден")
        return

    if not user.partner_id:
        await message.answer(
            "❌ Сначала пригласите собеседника!",
            reply_markup=kb.get_main_menu_keyboard(has_partner=False)
        )
        return

    # Получаем информацию о собеседнике
    partner_name = "нет"
    partner_stats = ""
    if user.partner_id:
        partner = db.query(User).filter(User.id == user.partner_id).first()
        if partner:
            partner_name = partner.full_name or f"@{partner.username}" if partner.username else "Собеседник"


    # ЗАДАЧИ КОТОРЫЕ Я НАЗНАЧИЛ (мои задачи для собеседника)
    my_tasks = db.query(Task).filter(
        Task.assigned_by_id == user.id,
        Task.completed == False
    ).all()

    # ЗАДАЧИ КОТОРЫЕ МНЕ НАЗНАЧИЛИ (задачи от собеседника для меня)
    tasks_for_me = db.query(Task).filter(
        Task.assigned_to_id == user.id,
        Task.completed == False
    ).all()

    response = f"📊 <b>ОБЗОР ЗАДАЧ</b>\n\n"

    if user.partner_id:
        response += f"👤 <b>Собеседник:</b> {partner_name}\n\n"

    # СТАТИСТИКА СОБЕСЕДНИКА
    response += partner_stats

    # РАЗДЕЛ 1: МОИ ЗАДАЧИ ДЛЯ СОБЕСЕДНИКА
    response += f"📤 <b>Мои задачи для {partner_name}:</b>\n"
    if my_tasks:
        for i, task in enumerate(my_tasks, 1):
            response += f"{i}. 📌 <b>{task.title}</b>\n"
            if task.description:
                response += f"   📝 {task.description}\n"
            response += f"   🕐 {task.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    else:
        response += "📭 Нет задач\n\n"

    # РАЗДЕЛ 2: ЗАДАЧИ ОТ СОБЕСЕДНИКА ДЛЯ МЕНЯ
    response += f"📥 <b>Задачи от {partner_name} для меня:</b>\n"
    if tasks_for_me:
        for i, task in enumerate(tasks_for_me, 1):
            response += f"{i}. 📌 <b>{task.title}</b>\n"
            if task.description:
                response += f"   📝 {task.description}\n"
            response += f"   🕐 {task.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    else:
        response += "📭 Нет задач\n\n"

    # АКТИВНЫЕ ЗАДАЧИ
    response += f"📊 <b>Активные задачи:</b>\n"
    response += f"• Мои задачи: {len(my_tasks)}\n"
    response += f"• Задачи для меня: {len(tasks_for_me)}\n"
    response += f"• Всего активных: {len(my_tasks) + len(tasks_for_me)}"

    await message.answer(response, parse_mode="HTML")