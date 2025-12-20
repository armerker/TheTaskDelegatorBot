import secrets
import string
from datetime import datetime, timedelta, date
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
import config
from database import User, Task, AppStats


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
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user:
        user.last_active_date = datetime.utcnow()
        user.total_messages_count = (user.total_messages_count or 0) + 1
        db.commit()


def update_app_stats(db: Session) -> None:
    """Обновляет общую статистику приложения"""
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

    # Подсчет OneSignal уведомлений
    onesignal_total = db.query(User).with_entities(
        db.func.sum(User.onesignal_notifications_sent)
    ).scalar() or 0

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


def get_app_stats_summary(db: Session) -> Dict[str, Any]:
    """Получает сводную статистику приложения"""
    stats = db.query(AppStats).first()

    if not stats:
        return {
            'total_users': 0,
            'active_users': 0,
            'total_tasks': 0,
            'completed_tasks': 0,
            'onesignal_notifications_total': 0
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


def increment_onesignal_stats(db: Session, user_id: int, sent: bool = True) -> None:
    """Увеличивает счетчик OneSignal уведомлений"""
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if user:
        if sent:
            user.onesignal_notifications_sent = (user.onesignal_notifications_sent or 0) + 1
        else:
            user.onesignal_notifications_received = (user.onesignal_notifications_received or 0) + 1
        db.commit()
        update_app_stats(db)