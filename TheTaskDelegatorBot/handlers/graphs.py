from aiogram import Router, F
from sqlalchemy.orm import Session
import keyboards as kb
from database import get_db
from graph_generator import GraphGenerator
import os
from datetime import datetime
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
router = Router()


@router.message(F.text == "📈 Графики")
async def show_graphs_menu(message: Message) -> None:
    """Показывает меню графиков"""
    db = next(get_db())

    # Очищаем старые графики
    generator = GraphGenerator(db)
    generator.cleanup_old_graphs()

    menu_text = (
        "📈 <b>МЕНЮ ГРАФИКОВ СТАТИСТИКИ</b>\n\n"
        "Выберите тип графика для генерации:\n\n"
        "👥 <b>Рост пользователей</b> - динамика регистрации пользователей\n"
        "✅ <b>Выполнение задач</b> - процент выполненных задач\n"
        "📅 <b>Активность</b> - активность пользователей за 30 дней\n"
        "🤝 <b>Партнеры</b> - распределение по партнерским связям\n"
        "📋 <b>Динамика задач</b> - создание и выполнение задач по дням\n"
        "🏆 <b>Топ продуктивность</b> - самые активные пользователи\n"
        "👤 <b>Моя статистика</b> - ваша личная продуктивность\n\n"
        "📊 <i>Графики генерируются на основе текущих данных</i>"
    )

    await message.answer(menu_text, parse_mode="HTML", reply_markup=kb.get_graphs_menu_keyboard())


@router.callback_query(F.data.startswith("graph:"))
async def handle_graph_callback(callback: CallbackQuery) -> None:
    """Обработчик нажатий на кнопки графиков"""
    graph_type = callback.data.split(":")[1]
    db = next(get_db())
    generator = GraphGenerator(db)

    # Показываем пользователю, что идет генерация
    await callback.answer(f"🔄 Генерирую {get_graph_name(graph_type)}...")

    try:
        graph_path = None

        # Генерируем соответствующий график
        if graph_type == "users_growth":
            graph_path = generator.generate_user_growth_graph()
            caption = (
                "📈 <b>ГРАФИК РОСТА ПОЛЬЗОВАТЕЛЕЙ</b>\n\n"
                "Показывает динамику регистрации новых пользователей с течением времени.\n"
                "Наклонная линия показывает общий тренд роста."
            )

        elif graph_type == "tasks_completion":
            graph_path = generator.generate_task_completion_graph()
            caption = (
                "✅ <b>ГРАФИК ВЫПОЛНЕНИЯ ЗАДАЧ</b>\n\n"
                "Отображает процент выполненных и ожидающих задач.\n"
                "Позволяет оценить общую продуктивность системы."
            )

        elif graph_type == "user_activity":
            graph_path = generator.generate_user_activity_graph()
            caption = (
                "📅 <b>ГРАФИК АКТИВНОСТИ ПОЛЬЗОВАТЕЛЕЙ</b>\n\n"
                "Показывает активность пользователей за последние 30 дней.\n"
                "Красным цветом выделена активность за сегодня."
            )

        elif graph_type == "partnership":
            graph_path = generator.generate_partnership_graph()
            caption = (
                "🤝 <b>ГРАФИК ПАРТНЕРСКИХ СВЯЗЕЙ</b>\n\n"
                "Показывает распределение пользователей с партнерами и без.\n"
                "Левый график - процентное соотношение, правый - количество."
            )

        elif graph_type == "task_timeline":
            graph_path = generator.generate_task_timeline_graph()
            caption = (
                "📋 <b>ДИНАМИКА СОЗДАНИЯ ЗАДАЧ</b>\n\n"
                "Показывает создание и выполнение задач по дням.\n"
                "Синие столбцы - всего задач, зеленые - выполнено."
            )

        elif graph_type == "top_productivity":
            graph_path = generator.generate_user_productivity_graph()
            caption = (
                "🏆 <b>ТОП-10 ПРОДУКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ</b>\n\n"
                "Рейтинг самых активных пользователей по количеству задач.\n"
                "Синие столбцы - созданные задачи, зеленые - выполненные."
            )

        elif graph_type == "my_stats":
            graph_path = generator.generate_user_productivity_graph(callback.from_user.id)
            if not graph_path:
                await callback.message.answer("❌ Не удалось сгенерировать ваш график статистики")
                return
            caption = (
                "👤 <b>ВАША ЛИЧНАЯ СТАТИСТИКА</b>\n\n"
                "Показывает вашу продуктивность в системе:\n"
                "• Создано - задачи, которые вы создали\n"
                "• Выполнено - задачи, которые вы выполнили\n"
                "• Получено - задачи, которые вам назначили\n"
                "• Удалено - задачи, которые вы удалили"
            )

        elif graph_type == "all_metrics":
            # Создаем и отправляем несколько графиков сразу
            await send_all_graphs(callback.message, db, generator)
            await callback.answer()
            return

        elif graph_type == "refresh_all":
            await callback.answer("🔄 Обновляю все графики...")
            await send_all_graphs(callback.message, db, generator)
            return

        elif graph_type == "previous":
            await callback.answer("◀️ Показываю предыдущий график")
            await show_navigation_graph(callback.message, db, -1)
            return

        elif graph_type == "next":
            await callback.answer("▶️ Показываю следующий график")
            await show_navigation_graph(callback.message, db, 1)
            return

        else:
            await callback.answer("❌ Неизвестный тип графика")
            return

        # Отправляем сгенерированный график
        if graph_path and os.path.exists(graph_path):
            photo = FSInputFile(graph_path)

            # Добавляем время генерации
            caption += f"\n\n🔄 <i>Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"

            await callback.message.answer_photo(
                photo=photo,
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb.get_graph_navigation_keyboard()
            )
        else:
            await callback.message.answer("❌ Не удалось сгенерировать график")

    except Exception as e:
        print(f"Ошибка генерации графика: {e}")
        await callback.message.answer(f"❌ Ошибка при генерации графика: {str(e)}")

    await callback.answer()


async def send_all_graphs(message: Message, db: Session, generator: GraphGenerator):
    """Отправляет все графики разом (галереей)"""
    try:
        # Генерируем все основные графики
        graphs_info = [
            ("📈 Рост пользователей", generator.generate_user_growth_graph),
            ("✅ Выполнение задач", generator.generate_task_completion_graph),
            ("📅 Активность", generator.generate_user_activity_graph),
            ("🤝 Партнеры", generator.generate_partnership_graph),
            ("📋 Динамика задач", generator.generate_task_timeline_graph),
            ("🏆 Топ продуктивность", lambda: generator.generate_user_productivity_graph()),
        ]

        # Генерируем личный график отдельно
        personal_graph = generator.generate_user_productivity_graph(message.from_user.id)

        media = []
        for name, graph_func in graphs_info:
            try:
                graph_path = graph_func()
                if graph_path and os.path.exists(graph_path):
                    photo = FSInputFile(graph_path)
                    media.append(InputMediaPhoto(
                        media=photo,
                        caption=f"<b>{name}</b>\n🔄 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                        parse_mode="HTML"
                    ))
            except Exception as e:
                print(f"Ошибка генерации {name}: {e}")

        # Отправляем галерею
        if media:
            await message.answer_media_group(media)

        # Отправляем личный график отдельно
        if personal_graph and os.path.exists(personal_graph):
            photo = FSInputFile(personal_graph)
            await message.answer_photo(
                photo=photo,
                caption="👤 <b>ВАША ЛИЧНАЯ СТАТИСТИКА</b>\n"
                        "Показатели вашей продуктивности в системе\n\n"
                        f"🔄 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                parse_mode="HTML"
            )

        await message.answer(
            "✅ Все графики сгенерированы!\n"
            "Вы можете выбрать конкретный график для детального просмотра.",
            reply_markup=kb.get_graphs_menu_keyboard()
        )

    except Exception as e:
        print(f"Ошибка отправки всех графиков: {e}")
        await message.answer(f"❌ Ошибка при создании графиков: {str(e)}")


async def show_navigation_graph(message: Message, db: Session, direction: int):
    """Показывает следующий/предыдущий график"""
    # Это упрощенная реализация - можно расширить для реальной навигации
    await message.answer(
        "🔧 Навигация по графикам в разработке...\n"
        "Пока что используйте меню для выбора конкретного графика.",
        reply_markup=kb.get_graphs_menu_keyboard()
    )


def get_graph_name(graph_type: str) -> str:
    """Возвращает читаемое название типа графика"""
    names = {
        "users_growth": "график роста пользователей",
        "tasks_completion": "график выполнения задач",
        "user_activity": "график активности",
        "partnership": "график партнерских связей",
        "task_timeline": "динамику задач",
        "top_productivity": "топ продуктивности",
        "my_stats": "вашу статистику",
        "all_metrics": "все графики",
        "refresh_all": "все графики"
    }
    return names.get(graph_type, "график")


@router.callback_query(F.data == "back_to_graphs")
async def back_to_graphs_menu(callback: CallbackQuery) -> None:
    """Возврат в меню графиков"""
    await show_graphs_menu(callback.message)
    await callback.answer()