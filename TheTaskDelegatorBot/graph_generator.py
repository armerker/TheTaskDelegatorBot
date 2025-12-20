import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import os
from database import User, Task, AppStats

# Настройки стиля графиков
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


class GraphGenerator:
    """Генератор графиков статистики"""

    def __init__(self, db: Session):
        self.db = db
        self.graphs_dir = "graphs"
        os.makedirs(self.graphs_dir, exist_ok=True)

    def _save_graph(self, filename: str) -> str:
        """Сохраняет график и возвращает путь к файлу"""
        path = os.path.join(self.graphs_dir, filename)
        plt.tight_layout()
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        return path

    def generate_user_growth_graph(self) -> str:
        """График роста пользователей"""
        # Получаем данные о пользователях по дате регистрации
        users = self.db.query(User).order_by(User.joined_date).all()

        if len(users) < 2:
            return self._generate_empty_graph("Недостаточно данных о пользователях")

        # Группируем по дням
        data = []
        for user in users:
            if user.joined_date:
                data.append({
                    'date': user.joined_date.date(),
                    'count': 1
                })

        df = pd.DataFrame(data)
        if df.empty:
            return self._generate_empty_graph("Недостаточно данных о пользователях")

        daily_counts = df.groupby('date').sum().cumsum()

        plt.figure(figsize=(12, 6))
        plt.plot(daily_counts.index, daily_counts['count'], marker='o', linewidth=3, markersize=8)
        plt.fill_between(daily_counts.index, daily_counts['count'], alpha=0.3)

        plt.title('📈 Рост пользователей с течением времени', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Дата регистрации', fontsize=12)
        plt.ylabel('Общее количество пользователей', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)

        # Добавляем аннотацию с текущим количеством
        current_count = len(users)
        plt.annotate(f'Всего: {current_count}',
                     xy=(1, 1), xycoords='axes fraction',
                     xytext=(-10, -10), textcoords='offset points',
                     ha='right', va='top',
                     bbox=dict(boxstyle='round,pad=0.5', fc='green', alpha=0.3),
                     fontsize=12)

        return self._save_graph('user_growth.png')

    def generate_task_completion_graph(self) -> str:
        """График выполнения задач"""
        tasks = self.db.query(Task).all()

        if not tasks:
            return self._generate_empty_graph("Нет данных о задачах")

        # Данные для графика
        total_tasks = len(tasks)
        completed = sum(1 for t in tasks if t.completed)
        pending = total_tasks - completed

        labels = ['Выполнено', 'В ожидании']
        sizes = [completed, pending]
        colors = ['#2ecc71', '#e74c3c']
        explode = (0.1, 0) if completed > 0 else (0, 0.1)

        plt.figure(figsize=(10, 8))
        plt.pie(sizes, explode=explode, labels=labels, colors=colors,
                autopct='%1.1f%%', shadow=True, startangle=90,
                textprops={'fontsize': 12})

        plt.title('📊 Статус выполнения задач', fontsize=16, fontweight='bold', pad=20)

        # Добавляем информацию в центре
        centre_circle = plt.Circle((0, 0), 0.70, fc='white')
        fig = plt.gcf()
        fig.gca().add_artist(centre_circle)

        plt.annotate(f'Всего задач:\n{total_tasks}',
                     xy=(0, 0), ha='center', va='center',
                     fontsize=14, fontweight='bold')

        return self._save_graph('task_completion.png')

    def generate_user_activity_graph(self) -> str:
        """График активности пользователей"""
        users = self.db.query(User).filter(User.last_active_date.isnot(None)).all()

        if len(users) < 2:
            return self._generate_empty_graph("Недостаточно данных об активности")

        # Группируем активность по дням
        now = datetime.utcnow()
        days = 30  # Последние 30 дней
        activity_counts = {i: 0 for i in range(days)}

        for user in users:
            if user.last_active_date:
                days_ago = (now - user.last_active_date).days
                if 0 <= days_ago < days:
                    activity_counts[days_ago] += 1

        # Готовим данные
        dates = [(now - timedelta(days=i)).strftime('%d.%m') for i in range(days)]
        dates.reverse()
        counts = [activity_counts[i] for i in range(days)]
        counts.reverse()

        plt.figure(figsize=(14, 6))
        bars = plt.bar(dates, counts, color='#3498db', alpha=0.8, edgecolor='darkblue')

        # Подсвечиваем сегодняшний день
        if counts[-1] > 0:
            bars[-1].set_color('#e74c3c')
            bars[-1].set_alpha(1)

        plt.title('📅 Активность пользователей за последние 30 дней',
                  fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Дата', fontsize=12)
        plt.ylabel('Активных пользователей', fontsize=12)
        plt.xticks(rotation=90)
        plt.grid(True, alpha=0.3, axis='y')

        # Добавляем значения на столбцы
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                plt.text(bar.get_x() + bar.get_width() / 2., height,
                         f'{int(height)}', ha='center', va='bottom', fontsize=9)

        return self._save_graph('user_activity.png')

    def generate_partnership_graph(self) -> str:
        """График партнерских связей"""
        users = self.db.query(User).all()

        if not users:
            return self._generate_empty_graph("Нет данных о пользователях")

        total_users = len(users)
        with_partner = sum(1 for u in users if u.partner_id)
        without_partner = total_users - with_partner

        # Создаем два графика рядом
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Круговая диаграмма
        labels = ['С партнером', 'Без партнера']
        sizes = [with_partner, without_partner]
        colors = ['#9b59b6', '#95a5a6']

        wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors,
                                           autopct='%1.1f%%', startangle=90,
                                           explode=(0.05, 0))

        ax1.set_title('🤝 Распределение по партнерским связям',
                      fontsize=14, fontweight='bold', pad=20)

        # Столбчатая диаграмма
        x = np.arange(len(labels))
        bars = ax2.bar(x, sizes, color=colors, alpha=0.8, edgecolor='black')

        ax2.set_title('Количество пользователей', fontsize=14, fontweight='bold', pad=20)
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels)
        ax2.set_ylabel('Количество')
        ax2.grid(True, alpha=0.3, axis='y')

        # Добавляем значения на столбцы
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width() / 2., height,
                     f'{int(height)}', ha='center', va='bottom', fontsize=12, fontweight='bold')

        # Общая информация
        fig.suptitle(f'📊 Партнерские связи (Всего пользователей: {total_users})',
                     fontsize=16, fontweight='bold', y=1.02)

        return self._save_graph('partnership.png')

    def generate_task_timeline_graph(self) -> str:
        """График создания задач по времени"""
        tasks = self.db.query(Task).order_by(Task.created_at).all()

        if len(tasks) < 3:
            return self._generate_empty_graph("Недостаточно данных о задачах")

        # Группируем задачи по дням
        task_dates = {}
        for task in tasks:
            date = task.created_at.date() if task.created_at else datetime.utcnow().date()
            if date not in task_dates:
                task_dates[date] = {'total': 0, 'completed': 0}
            task_dates[date]['total'] += 1
            if task.completed:
                task_dates[date]['completed'] += 1

        dates = sorted(task_dates.keys())
        total_tasks = [task_dates[d]['total'] for d in dates]
        completed_tasks = [task_dates[d]['completed'] for d in dates]

        # Преобразуем даты в строки для отображения
        date_labels = [d.strftime('%d.%m') for d in dates]

        plt.figure(figsize=(14, 7))

        x = np.arange(len(dates))
        width = 0.35

        plt.bar(x - width / 2, total_tasks, width, label='Всего задач', color='#3498db', alpha=0.8)
        plt.bar(x + width / 2, completed_tasks, width, label='Выполнено', color='#2ecc71', alpha=0.8)

        plt.title('📋 Динамика создания и выполнения задач',
                  fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Дата', fontsize=12)
        plt.ylabel('Количество задач', fontsize=12)
        plt.xticks(x, date_labels, rotation=45)
        plt.legend()
        plt.grid(True, alpha=0.3, axis='y')

        # Добавляем линию тренда
        if len(total_tasks) > 2:
            z = np.polyfit(x, total_tasks, 1)
            p = np.poly1d(z)
            plt.plot(x, p(x), "r--", alpha=0.5, label='Тренд')
            plt.legend()

        return self._save_graph('task_timeline.png')

    def generate_user_productivity_graph(self, telegram_id: int = None) -> Optional[str]:
        """График продуктивности пользователя (или всех пользователей)"""
        if telegram_id:
            # Личная статистика пользователя
            user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return None

            data = {
                'Создано': getattr(user, 'tasks_created_count', 0),
                'Выполнено': getattr(user, 'tasks_completed_count', 0),
                'Получено': getattr(user, 'tasks_received_count', 0),
                'Удалено': getattr(user, 'tasks_deleted_count', 0)
            }

            plt.figure(figsize=(10, 6))
            colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c']
            bars = plt.bar(data.keys(), data.values(), color=colors, alpha=0.8)

            plt.title(f'📊 Продуктивность: {user.full_name or "Пользователь"}',
                      fontsize=16, fontweight='bold', pad=20)
            plt.ylabel('Количество задач', fontsize=12)
            plt.grid(True, alpha=0.3, axis='y')

            # Добавляем значения на столбцы
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width() / 2., height,
                         f'{int(height)}', ha='center', va='bottom', fontsize=11, fontweight='bold')

            return self._save_graph(f'user_productivity_{telegram_id}.png')
        else:
            # Топ-10 самых продуктивных пользователей
            users = self.db.query(User).all()

            if len(users) < 2:
                return self._generate_empty_graph("Недостаточно данных о пользователях")

            # Считаем общую продуктивность (создано + выполнено)
            user_productivity = []
            for user in users:
                created = getattr(user, 'tasks_created_count', 0)
                completed = getattr(user, 'tasks_completed_count', 0)
                productivity = created + completed
                if productivity > 0:
                    user_productivity.append({
                        'name': user.full_name or f"User {user.id}",
                        'productivity': productivity,
                        'created': created,
                        'completed': completed
                    })

            if not user_productivity:
                return self._generate_empty_graph("Нет данных о продуктивности")

            # Сортируем и берем топ-10
            user_productivity.sort(key=lambda x: x['productivity'], reverse=True)
            top_users = user_productivity[:10]

            names = [u['name'][:15] + '...' if len(u['name']) > 15 else u['name'] for u in top_users]
            productivity = [u['productivity'] for u in top_users]
            created = [u['created'] for u in top_users]
            completed = [u['completed'] for u in top_users]

            x = np.arange(len(names))
            width = 0.35

            plt.figure(figsize=(14, 8))
            plt.bar(x - width / 2, created, width, label='Создано', color='#3498db', alpha=0.8)
            plt.bar(x + width / 2, completed, width, label='Выполнено', color='#2ecc71', alpha=0.8)

            plt.title('🏆 Топ-10 самых продуктивных пользователей',
                      fontsize=16, fontweight='bold', pad=20)
            plt.xlabel('Пользователь', fontsize=12)
            plt.ylabel('Количество задач', fontsize=12)
            plt.xticks(x, names, rotation=45, ha='right')
            plt.legend()
            plt.grid(True, alpha=0.3, axis='y')

            return self._save_graph('top_productivity.png')

    def _generate_empty_graph(self, message: str) -> str:
        """Создает пустой график с сообщением"""
        plt.figure(figsize=(8, 6))
        plt.text(0.5, 0.5, message,
                 ha='center', va='center',
                 fontsize=14, fontweight='bold',
                 transform=plt.gca().transAxes)
        plt.title('📊 График статистики', fontsize=16, fontweight='bold')
        return self._save_graph('empty_graph.png')

    def cleanup_old_graphs(self, hours: int = 1):
        """Удаляет старые графики"""
        try:
            for filename in os.listdir(self.graphs_dir):
                filepath = os.path.join(self.graphs_dir, filename)
                if os.path.isfile(filepath):
                    # Проверяем время создания
                    creation_time = datetime.fromtimestamp(os.path.getctime(filepath))
                    if datetime.now() - creation_time > timedelta(hours=hours):
                        os.remove(filepath)
        except Exception as e:
            print(f"⚠️ Ошибка очистки графиков: {e}")