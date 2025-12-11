from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session
import keyboards as kb
from database import get_db

router = Router()

class InviteStates(StatesGroup):
    waiting_for_code = State()

@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    db = next(get_db())
    from database import User

    args = message.text.split()
    if len(args) > 1:
        invite_code = args[1]
        from handlers.invite import process_invite_code
        success = await process_invite_code(message, invite_code, state)
        if success:
            return

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        db.add(user)
        db.commit()

    await show_main_menu(message, user, db)

async def show_main_menu(message: Message, user=None, db_session=None):
    """Показывает главное меню"""
    if not user:
        if not db_session:
            db_session = next(get_db())
        from database import User
        user = db_session.query(User).filter(User.telegram_id == message.from_user.id).first()

    welcome_text = (
        "👋 Добро пожаловать в TaskBuddy!\n\n"
        "📌 Здесь вы можете обмениваться задачами с вашим собеседником.\n\n"
    )

    if user and user.partner_id:
        if not db_session:
            db_session = next(get_db())
        from database import User
        partner = db_session.query(User).filter(User.id == user.partner_id).first()
        if partner:
            partner_name = partner.full_name or "Собеседник"
            partner_username = f"@{partner.username}" if partner.username else ""
            welcome_text += f"🤝 <b>Ваш собеседник:</b> {partner_name} {partner_username}\n\n"
            # Краткая статистика
            welcome_text += f"📊 <b>Ваша статистика:</b>\n"
            welcome_text += f"• Создано: {getattr(user, 'tasks_created_count', 0)}\n"
            welcome_text += f"• Выполнено: {getattr(user, 'tasks_completed_count', 0)}\n"
            welcome_text += f"• Получено: {getattr(user, 'tasks_received_count', 0)}\n\n"
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
async def back_to_menu(message: Message):
    """Возврат в главное меню"""
    await show_main_menu(message)

@router.message(F.text == "🔍 Найти собеседника")
async def find_partner_menu(message: Message):
    """Меню поиска собеседника"""
    db = next(get_db())
    from database import User

    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user:
        # Если пользователь не найден, создаем его и показываем меню поиска
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        db.add(user)
        db.commit()
        # Показываем меню поиска
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
            partner_name = partner.full_name or "Собеседник"
            partner_username = f"@{partner.username}" if partner.username else ""
            await message.answer(f"✅ У вас уже есть собеседник: {partner_name} {partner_username}")
        else:
            await message.answer("✅ У вас уже есть собеседник!")
        # Возвращаем в главное меню
        await show_main_menu(message)
        return

    # Если пользователь существует и у него нет собеседника, показываем меню поиска
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
async def back_to_menu_callback(callback: CallbackQuery):
    """Возврат в главное меню из inline-кнопки"""
    await show_main_menu(callback.message)
    await callback.answer()