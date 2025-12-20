from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_main_menu_keyboard(has_partner: bool = False) -> ReplyKeyboardMarkup:
    """Создает главное меню"""
    builder = ReplyKeyboardBuilder()

    if not has_partner:
        builder.add(KeyboardButton(text="🔍 Найти собеседника"))
        builder.add(KeyboardButton(text="📊 Статистика"))
        builder.add(KeyboardButton(text="📈 Графики"))  # Новая кнопка!
        builder.add(KeyboardButton(text="🌐 Web Notifications"))
    else:
        builder.add(KeyboardButton(text="📝 Создать задание"))
        builder.add(KeyboardButton(text="📋 Мои задачи"))
        builder.add(KeyboardButton(text="📊 Статистика"))
        builder.add(KeyboardButton(text="📈 Графики"))  # Новая кнопка!
        builder.add(KeyboardButton(text="🌐 Web Notifications"))
        builder.add(KeyboardButton(text="🗑️ Удалить задачу"))
        builder.add(KeyboardButton(text="✅ Выполнил задачу"))
        builder.add(KeyboardButton(text="🔗 Отвязать собеседника"))

    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру с кнопкой 'Назад'"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад в меню")]],
        resize_keyboard=True
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру с кнопкой 'Отмена'"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )


def get_tasks_keyboard(tasks: list, action: str, show_back: bool = True) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора задач"""
    builder = InlineKeyboardBuilder()

    for task in tasks:
        emoji: str = "✅" if task.completed else "📌"
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


def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения действия"""
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


def get_onesignal_menu_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для меню OneSignal"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔔 Тест OneSignal")],
            [KeyboardButton(text="📝 Web напоминание")],
            [KeyboardButton(text="📊 Статистика API")],
            [KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="⬅️ Назад в меню")]
        ],
        resize_keyboard=True
    )


def get_graphs_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура меню графиков"""
    builder = InlineKeyboardBuilder()

    # Первый ряд
    builder.add(InlineKeyboardButton(
        text="👥 Рост пользователей",
        callback_data="graph:users_growth"
    ))
    builder.add(InlineKeyboardButton(
        text="✅ Выполнение задач",
        callback_data="graph:tasks_completion"
    ))

    # Второй ряд
    builder.add(InlineKeyboardButton(
        text="📅 Активность",
        callback_data="graph:user_activity"
    ))
    builder.add(InlineKeyboardButton(
        text="🤝 Партнеры",
        callback_data="graph:partnership"
    ))

    # Третий ряд
    builder.add(InlineKeyboardButton(
        text="📋 Динамика задач",
        callback_data="graph:task_timeline"
    ))
    builder.add(InlineKeyboardButton(
        text="🏆 Топ продуктивность",
        callback_data="graph:top_productivity"
    ))

    # Четвертый ряд
    builder.add(InlineKeyboardButton(
        text="👤 Моя статистика",
        callback_data="graph:my_stats"
    ))
    builder.add(InlineKeyboardButton(
        text="🔢 Все метрики",
        callback_data="graph:all_metrics"
    ))

    # Пятый ряд
    builder.add(InlineKeyboardButton(
        text="🔄 Обновить все графики",
        callback_data="graph:refresh_all"
    ))

    # Шестой ряд
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад в меню",
        callback_data="back_to_menu"
    ))

    builder.adjust(2, 2, 2, 2, 1, 1)  # Настройка расположения кнопок
    return builder.as_markup()


def get_graph_navigation_keyboard() -> InlineKeyboardMarkup:
    """Навигация между графиками"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="◀️ Предыдущий",
        callback_data="graph:previous"
    ))
    builder.add(InlineKeyboardButton(
        text="🏠 Меню графиков",
        callback_data="back_to_graphs"
    ))
    builder.add(InlineKeyboardButton(
        text="▶️ Следующий",
        callback_data="graph:next"
    ))

    builder.adjust(3)
    return builder.as_markup()


def get_graph_types_keyboard() -> InlineKeyboardMarkup:
    """Типы графиков для детального просмотра"""
    builder = InlineKeyboardBuilder()

    graph_types = [
        ("📊 Столбчатая", "bar"),
        ("📈 Линейная", "line"),
        ("🥧 Круговая", "pie"),
        ("📉 Область", "area"),
        ("📊 Гистограмма", "hist"),
        ("📊 Точечная", "scatter")
    ]

    for name, callback in graph_types:
        builder.add(InlineKeyboardButton(
            text=name,
            callback_data=f"graph_type:{callback}"
        ))

    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к графикам",
        callback_data="back_to_graphs"
    ))

    builder.adjust(2)
    return builder.as_markup()