from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session
import keyboards as kb
from database import get_db
import utils

router = Router()


class InviteStates(StatesGroup):
    waiting_for_code = State()


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext) -> None:
    """Обработчик команды /start"""
    db: Session = next(get_db())
    from database import User

    # Обновляем статистику активности
    utils.update_user_activity(db, message.from_user.id)

    args: list[str] = message.text.split()
    if len(args) > 1:
        invite_code: str = args[1]
        from handlers.invite import process_invite_code
        success: bool = await process_invite_code(message, invite_code, state)
        if success:
            return

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            joined_date=utils.datetime.utcnow(),
            last_active_date=utils.datetime.utcnow()
        )
        db.add(user)
        db.commit()
        # Обновляем общую статистику
        utils.update_app_stats(db)

    await show_main_menu(message, user, db)


async def show_main_menu(message: Message, user=None, db_session=None) -> None:
    """Показывает главное меню"""
    if not user:
        if not db_session:
            db_session = next(get_db())
        from database import User
        user = db_session.query(User).filter(User.telegram_id == message.from_user.id).first()

    # Обновляем активность
    utils.update_user_activity(db_session, message.from_user.id)

    welcome_text: str = (
        "👋 Добро пожаловать в TaskBuddy!\n\n"
        "📌 Здесь вы можете обмениваться задачами с вашим собеседником.\n\n"
    )

    if user and user.partner_id:
        if not db_session:
            db_session = next(get_db())
        from database import User
        partner = db_session.query(User).filter(User.id == user.partner_id).first()
        if partner:
            partner_name: str = partner.full_name or "Собеседник"
            partner_username: str = f"@{partner.username}" if partner.username else ""
            welcome_text += f"🤝 <b>Ваш собеседник:</b> {partner_name} {partner_username}\n\n"
            # Краткая статистика
            welcome_text += f"📊 <b>Ваша статистика:</b>\n"
            welcome_text += f"• Создано: {getattr(user, 'tasks_created_count', 0)}\n"
            welcome_text += f"• Выполнено: {getattr(user, 'tasks_completed_count', 0)}\n"
            welcome_text += f"• Получено: {getattr(user, 'tasks_received_count', 0)}\n"
            welcome_text += f"• Активность: {(utils.datetime.utcnow() - user.joined_date).days if user.joined_date else 0} дней\n\n"
            welcome_text += "Выберите действие:"
        else:
            welcome_text += "🤝 <b>Собеседник:</b> загрузка...\n\nВыберите действие:"
    else:
        welcome_text += "❌ У вас нет собеседника.\n\nНайдите собеседника чтобы начать!"

    await message.answer(
        welcome_text,
        reply_markup=kb.get_main_menu_keyboard(has_partner=bool(user.partner_id if user else False)),
        parse_mode="HTML"
    )


@router.message(F.text == "⬅️ Назад в меню")
async def back_to_menu(message: Message) -> None:
    """Возврат в главное меню"""
    db = next(get_db())
    utils.update_user_activity(db, message.from_user.id)
    await show_main_menu(message)


@router.message(F.text == "🔍 Найти собеседника")
async def find_partner_menu(message: Message) -> None:
    """Меню поиска собеседника"""
    db: Session = next(get_db())
    from database import User

    utils.update_user_activity(db, message.from_user.id)

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            joined_date=utils.datetime.utcnow(),
            last_active_date=utils.datetime.utcnow()
        )
        db.add(user)
        db.commit()
        utils.update_app_stats(db)

        await message.answer(
            "🔍 <b>Найти собеседника:</b>\n\n"
            "1. <b>Создать свой код</b> - вы создаете код, который отправляете другу\n"
            "2. <b>Ввести код друга</b> - если друг уже создал код\n\n"
            "Выберите действие:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🎫 Создать свой код")],
                    [KeyboardButton(text="⌨️ Ввести код друга")],
                    [KeyboardButton(text="⬅️ Назад в меню")]
                ],
                resize_keyboard=True
            ),
            parse_mode="HTML"
        )
        return

    if user.partner_id:
        partner = db.query(User).filter(User.id == user.partner_id).first()
        if partner:
            partner_name: str = partner.full_name or "Собеседник"
            partner_username: str = f"@{partner.username}" if partner.username else ""
            await message.answer(f"✅ У вас уже есть собеседник: {partner_name} {partner_username}")
        else:
            await message.answer("✅ У вас уже есть собеседник!")

        await show_main_menu(message)
        return

    await message.answer(
        "🔍 <b>Найти собеседника:</b>\n\n"
        "1. <b>Создать свой код</b> - вы создаете код, который отправляете другу\n"
        "2. <b>Ввести код друга</b> - если друг уже создал код\n\n"
        "Выберите действие:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🎫 Создать свой код")],
                [KeyboardButton(text="⌨️ Ввести код друга")],
                [KeyboardButton(text="⬅️ Назад в меню")]
            ],
            resize_keyboard=True
        ),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback: CallbackQuery) -> None:
    """Возврат в главное меню из inline-кнопки"""
    db = next(get_db())
    utils.update_user_activity(db, callback.from_user.id)
    await show_main_menu(callback.message)
    await callback.answer()