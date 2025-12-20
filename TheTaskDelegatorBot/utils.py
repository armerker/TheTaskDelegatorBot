import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
import config
from database import User, Task, AppStats, engine


def generate_invite_code(length: int = 6) -> str:
    """Генерирует простой код приглашения"""
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_invite(db: Session, user_id: int) -> Tuple[Optional[str], Optional[datetime]]:
    """Создает инвайт-код для пользователя"""
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        return None, None

    invite_code = generate_invite_code()
    expires_at = datetime.utcnow() + timedelta(hours=config.config.INVITE_LINK_EXPIRE_HOURS)

    user.invite_code = invite_code
    user.invite_expires = expires_at

    db.commit()
    return invite_code, expires_at


def accept_invite(db: Session, invite_code: str, new_user_id: int) -> Tuple[bool, Optional[int], str]:
    """Принимает инвайт-код"""
    invite_code = invite_code.upper().strip()

    inviting_user = db.query(User).filter(
        User.invite_code == invite_code,
        User.invite_expires > datetime.utcnow()
    ).first()

    if not inviting_user:
        return False, None, "❌ Неверный или просроченный код приглашения"

    if inviting_user.partner_id:
        return False, None, "❌ У этого пользователя уже есть собеседник"

    if inviting_user.telegram_id == new_user_id:
        return False, None, "❌ Нельзя присоединиться к самому себе"

    new_user = db.query(User).filter(User.telegram_id == new_user_id).first()
    if not new_user:
        return False, None, "❌ Пользователь не найден"

    if new_user.partner_id:
        return False, None, "❌ У вас уже есть собеседник"

    inviting_user.partner_id = new_user.id
    new_user.partner_id = inviting_user.id

    inviting_user.invite_code = None
    inviting_user.invite_expires = None

    db.commit()

    partner_name = inviting_user.full_name or "пользователю"
    return True, inviting_user.id, f"✅ Вы успешно подключились к {partner_name}!"


def update_user_activity(db: Session, telegram_id: int) -> None:
    """Обновляет статистику активности пользователя"""
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            # Обновляем дату активности
            user.last_active_date = datetime.utcnow()

            # Увеличиваем счетчик сообщений
            current = getattr(user, 'total_messages_count', 0) or 0
            user.total_messages_count = current + 1

            db.commit()
    except Exception as e:
        print(f"⚠️ Ошибка обновления активности: {e}")


def update_app_stats(db: Session) -> None:
    """Обновляет общую статистику приложения"""
    try:
        # Подсчет пользователей
        total_users = db.query(User).count()

        # Активные пользователи (были активны в последние 7 дней)
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_users = db.query(User).filter(
            User.last_active_date >= week_ago
        ).count()

        # Подсчет задач
        total_tasks = db.query(Task).count()
        completed_tasks = db.query(Task).filter(Task.completed == True).count()

        # Подсчет OneSignal уведомлений - УПРОЩЕННЫЙ вариант
        onesignal_total = 0
        users = db.query(User).all()
        for user in users:
            sent = getattr(user, 'onesignal_notifications_sent', 0) or 0
            onesignal_total += sent

        # Обновляем или создаем запись статистики
        stats = db.query(AppStats).first()
        if not stats:
            stats = AppStats()
            db.add(stats)

        stats.total_users = total_users
        stats.active_users = active_users
        stats.total_tasks = total_tasks
        stats.completed_tasks = completed_tasks
        stats.onesignal_notifications_total = onesignal_total
        stats.updated_at = datetime.utcnow()

        db.commit()
        print(f"✅ Статистика обновлена: {total_users} пользователей, {total_tasks} задач")

    except Exception as e:
        print(f"⚠️ Ошибка обновления статистики приложения: {e}")


def get_app_stats_summary(db: Session) -> Dict[str, Any]:
    """Получает сводную статистику приложения"""
    try:
        stats = db.query(AppStats).first()

        if not stats:
            return {
                'total_users': 0,
                'active_users': 0,
                'users_with_partner': 0,
                'partner_rate': 0,
                'total_tasks': 0,
                'completed_tasks': 0,
                'active_tasks': 0,
                'completion_rate': 0,
                'onesignal_notifications_total': 0,
                'updated_at': datetime.utcnow()
            }

        # Дополнительная статистика
        users_with_partner = db.query(User).filter(User.partner_id.isnot(None)).count()
        active_tasks = db.query(Task).filter(Task.completed == False).count()

        # Процент выполнения задач
        completion_rate = 0
        if stats.total_tasks > 0:
            completion_rate = (stats.completed_tasks / stats.total_tasks) * 100

        # Процент пользователей с партнерами
        partner_rate = 0
        if stats.total_users > 0:
            partner_rate = (users_with_partner / stats.total_users) * 100

        return {
            'total_users': stats.total_users,
            'active_users': stats.active_users,
            'users_with_partner': users_with_partner,
            'partner_rate': partner_rate,
            'total_tasks': stats.total_tasks,
            'completed_tasks': stats.completed_tasks,
            'active_tasks': active_tasks,
            'completion_rate': completion_rate,
            'onesignal_notifications_total': stats.onesignal_notifications_total,
            'updated_at': stats.updated_at
        }
    except Exception as e:
        print(f"⚠️ Ошибка получения статистики: {e}")
        return {
            'total_users': 0,
            'active_users': 0,
            'users_with_partner': 0,
            'partner_rate': 0,
            'total_tasks': 0,
            'completed_tasks': 0,
            'active_tasks': 0,
            'completion_rate': 0,
            'onesignal_notifications_total': 0,
            'updated_at': datetime.utcnow()
        }


def increment_onesignal_stats(db: Session, user_id: int, sent: bool = True) -> None:
    """Увеличивает счетчик OneSignal уведомлений"""
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            if sent:
                current = getattr(user, 'onesignal_notifications_sent', 0) or 0
                user.onesignal_notifications_sent = current + 1
            else:
                current = getattr(user, 'onesignal_notifications_received', 0) or 0
                user.onesignal_notifications_received = current + 1
            db.commit()
            update_app_stats(db)
    except Exception as e:
        print(f"⚠️ Ошибка обновления OneSignal статистики: {e}")


def get_user_stats_for_graph(db, user_id: int) -> dict:
    """Получает статистику пользователя для графиков"""
    user = db.query(User).filter(User.telegram_id == user_id).first()

    if not user:
        return {}

    return {
        'tasks_created': getattr(user, 'tasks_created_count', 0),
        'tasks_completed': getattr(user, 'tasks_completed_count', 0),
        'tasks_received': getattr(user, 'tasks_received_count', 0),
        'tasks_deleted': getattr(user, 'tasks_deleted_count', 0),
        'messages_count': getattr(user, 'total_messages_count', 0),
        'days_in_app': (datetime.utcnow() - user.joined_date).days if user.joined_date else 0,
        'last_active': user.last_active_date,
        'has_partner': bool(user.partner_id)
    }