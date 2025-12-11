from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_main_menu_keyboard(has_partner: bool = False):
    builder = ReplyKeyboardBuilder()

    if not has_partner:
        builder.add(KeyboardButton(text="🔍 Найти собеседника"))
    else:
        builder.add(KeyboardButton(text="📝 Создать задание"))
        builder.add(KeyboardButton(text="🗑️ Удалить задачу"))
        builder.add(KeyboardButton(text="✅ Выполнил задачу"))
        builder.add(KeyboardButton(text="📋 Мои задачи"))
        builder.add(KeyboardButton(text="📊 Статистика"))
        builder.add(KeyboardButton(text="🔗 Отвязать собеседника"))

    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад в меню")]],
        resize_keyboard=True
    )


def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )


def get_tasks_keyboard(tasks, action: str, show_back: bool = True):
    builder = InlineKeyboardBuilder()

    for task in tasks:
        emoji = "✅" if task.completed else "📌"
        builder.add(InlineKeyboardButton(
            text=f"{emoji} {task.title[:20]}...",
            callback_data=f"{action}:{task.id}"
        ))

    if show_back:
        builder.add(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="back_to_menu"
        ))

    builder.adjust(1)
    return builder.as_markup()


def get_confirmation_keyboard(action: str):
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="✅ Да",
        callback_data=f"confirm_{action}"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ Нет",
        callback_data="cancel_action"
    ))

    return builder.as_markup()