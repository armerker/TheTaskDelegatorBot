import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
import config


def generate_invite_code(length: int = 6) -> str:
    """Генерирует простой код приглашения"""
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_invite(db: Session, user_id: int) -> Tuple[Optional[str], Optional[datetime]]:
    """Создает инвайт-код для пользователя"""
    from database import User

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
    from database import User

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