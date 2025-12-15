from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import Session
import keyboards as kb
import utils
from database import get_db
from handlers.main_menu import InviteStates, show_main_menu

router = Router()


async def send_notification(user_id: int, text: str) -> bool:
    """Отправляет уведомление пользователю"""
    try:
        from bot import bot_instance as bot
        print(f"🔄 Попытка отправить уведомление пользователю {user_id}")
        result = await bot.send_message(user_id, text, parse_mode="HTML")
        print(f"✅ Уведомление отправлено пользователю {user_id}")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления пользователю {user_id}: {type(e).__name__}: {e}")
        return False


@router.message(F.text == "🎫 Создать свой код")
async def create_invite_code(message: Message) -> None:
    """Создать инвайт-код"""
    db: Session = next(get_db())
    from database import User

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    if user.partner_id:
        await message.answer("✅ У вас уже есть собеседник!")
        return


    invite_code, expires_at = utils.create_invite(db, message.from_user.id)

    if not invite_code:
        await message.answer("❌ Не удалось создать приглашение")
        return

    expires_str: str = expires_at.strftime("%d.%m.%Y %H:%M")


    await message.answer(
        f"🎉 <b>Ваш код приглашения создан!</b>\n\n"
        f"<code>{invite_code}</code>\n\n"
        f"⏳ <b>Действует до:</b> {expires_str}\n\n"
        f"<b>Отправьте другу:</b>\n"
        f"1. Код: <code>{invite_code}</code>\n"
        f"2. Или ссылку: https://t.me/TheTaskDelegatorBot?start={invite_code}\n\n"
        f"<b>Как подключиться:</b>\n"
        f"Друг должен:\n"
        f"1. Перейти по ссылке\n"
        f"2. Или ввести код через '⌨️ Ввести код друга'",
        parse_mode="HTML"
    )


@router.message(F.text == "⌨️ Ввести код друга")
async def enter_invite_code(message: Message, state: FSMContext) -> None:
    """Начать ввод инвайт-кода"""
    db: Session = next(get_db())
    from database import User

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    if user.partner_id:
        await message.answer("✅ У вас уже есть собеседник!")
        return

    await state.set_state(InviteStates.waiting_for_code)
    await message.answer(
        "⌨️ <b>Введите код приглашения:</b>\n\n"
        "Код состоит из 6 символов (буквы и цифры)\n"
        "Пример: <code>A1B2C3</code>\n\n"
        "Введите код, который вам отправил друг:",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(InviteStates.waiting_for_code)
async def process_invite_code_input(message: Message, state: FSMContext) -> None:
    """Обработать введенный код"""
    if message.text == "❌ Отмена":
        await state.clear()
        await show_main_menu(message)
        return

    invite_code: str = message.text.strip().upper()

    # Проверяем формат кода (6 символов, буквы/цифры)
    if len(invite_code) != 6 or not all(c.isalnum() for c in invite_code):
        await message.answer("❌ Неверный формат кода! Код должен состоять из 6 букв/цифр.\nПопробуйте еще раз:")
        return

    # Обрабатываем код
    success: bool = await process_invite_code(message, invite_code, state)

    if success:
        await state.clear()


async def process_invite_code(message: Message, invite_code: str, state: FSMContext = None) -> bool:
    """Обработать код приглашения"""
    db: Session = next(get_db())

    success: bool
    partner_id: int
    response: str
    success, partner_id, response = utils.accept_invite(db, invite_code, message.from_user.id)

    if success:
        # Получаем информацию о собеседнике
        from database import User
        partner = db.query(User).filter(User.id == partner_id).first()
        partner_name: str = partner.full_name or "Собеседник"
        user_name: str = message.from_user.full_name or "Пользователь"

        await message.answer(
            f"✅ Вы успешно подключились к {partner_name}!\n\n"
            f"Теперь вы можете обмениваться задачами!"
        )

        # Уведомляем собеседника
        notification_text: str = f"✅ {user_name} подключился к вам!\n\nТеперь вы можете обмениваться задачами!"
        await send_notification(partner.telegram_id, notification_text)

        await show_main_menu(message)
        return True
    else:
        await message.answer(response)
        return False


@router.message(F.text == "🔗 Отвязать собеседника")
async def unbind_partner(message: Message) -> None:
    """Отвязать собеседника"""
    db: Session = next(get_db())
    from database import User

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user or not user.partner_id:
        await message.answer(
            "❌ У вас нет привязанного собеседника!",
            reply_markup=kb.get_main_menu_keyboard(has_partner=False)
        )
        return

    partner = db.query(User).filter(User.id == user.partner_id).first()
    partner_name: str = partner.full_name or "Собеседник"

    # Подтверждение
    await message.answer(
        f"⚠️ <b>Отвязать собеседника?</b>\n\n"
        f"Вы собираетесь отвязать {partner_name}\n\n"
        f"<b>ВНИМАНИЕ:</b> Все ваши общие задачи будут удалены!\n\n"
        f"После отвязки вы:\n"
        f"- Не сможете обмениваться задачами\n"
        f"- Все текущие задачи будут удалены\n"
        f"- Статистика будет сброшена\n"
        f"- Нужно будет создавать новое подключение",
        reply_markup=kb.get_confirmation_keyboard("unbind"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_unbind")
async def confirm_unbind_partner(callback: CallbackQuery) -> None:
    """Подтверждение отвязки собеседника"""
    db: Session = next(get_db())
    from database import User, Task

    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

    if not user or not user.partner_id:
        await callback.message.answer("❌ У вас нет привязанного собеседника!")
        await callback.answer()
        return

    partner = db.query(User).filter(User.id == user.partner_id).first()
    partner_name: str = partner.full_name or "Собеседник"
    user_name: str = callback.from_user.full_name or "Пользователь"


    tasks_assigned: list[Task] = db.query(Task).filter(Task.assigned_by_id == user.id).all()

    tasks_received: list[Task] = db.query(Task).filter(Task.assigned_to_id == user.id).all()

    # Удаляем все задачи
    for task in tasks_assigned:
        db.delete(task)
    for task in tasks_received:
        db.delete(task)

    # СБРАСЫВАЕМ СТАТИСТИКУ (безопасно)
    try:
        user.tasks_created_count = 0
        user.tasks_completed_count = 0
        user.tasks_received_count = 0
        user.tasks_deleted_count = 0

        if partner:
            partner.tasks_created_count = 0
            partner.tasks_completed_count = 0
            partner.tasks_received_count = 0
            partner.tasks_deleted_count = 0
    except:
        pass


    user.partner_id = None
    if partner:
        partner.partner_id = None

    db.commit()

    # Уведомляем собеседника
    if partner:
        notification_text: str = (
            f"⚠️ {user_name} отвязался от вас!\n\n"
            f"Все общие задачи удалены.\n"
            f"Статистика сброшена."
        )
        await send_notification(partner.telegram_id, notification_text)


    await callback.message.answer(
        f"🔗 Собеседник <b>{partner_name}</b> отвязан!\n"
        f"Все задачи удалены, статистика сброшена.",
        parse_mode="HTML"
    )

    # Возвращаем в меню
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=kb.get_main_menu_keyboard(has_partner=False)
    )
    await callback.answer()


@router.message(Command("invite"))
async def invite_command(message: Message) -> None:
    """Команда /invite для принятия кода"""
    args: list[str] = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /invite <код_приглашения>")
        return

    invite_code: str = args[1].upper()
    await process_invite_code(message, invite_code)