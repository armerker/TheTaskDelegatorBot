from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

engine = create_engine(DATABASE_URL,
                       connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    full_name = Column(String)
    partner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    invite_code = Column(String, unique=True, nullable=True)
    invite_expires = Column(DateTime, nullable=True)

    # Статистика задач
    tasks_created_count = Column(Integer, default=0)
    tasks_completed_count = Column(Integer, default=0)
    tasks_received_count = Column(Integer, default=0)
    tasks_deleted_count = Column(Integer, default=0)

    # Статистика активности
    total_messages_count = Column(Integer, default=0)  # Всего сообщений от пользователя
    last_active_date = Column(DateTime, default=datetime.utcnow)  # Последняя активность
    joined_date = Column(DateTime, default=datetime.utcnow)  # Дата регистрации

    # Внешние API статистика
    onesignal_notifications_sent = Column(Integer, default=0)  # Отправлено через OneSignal
    onesignal_notifications_received = Column(Integer, default=0)  # Получено через OneSignal

    tasks_assigned = relationship("Task", foreign_keys="Task.assigned_by_id", back_populates="assigned_by")
    tasks_received = relationship("Task", foreign_keys="Task.assigned_to_id", back_populates="assigned_to")


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    assigned_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    assigned_by = relationship("User", foreign_keys=[assigned_by_id], back_populates="tasks_assigned")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], back_populates="tasks_received")


class AppStats(Base):
    __tablename__ = 'app_stats'

    id = Column(Integer, primary_key=True)
    total_users = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    onesignal_notifications_total = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)


def init_db() -> None:
    """Инициализирует базу данных и добавляет недостающие столбцы"""
    Base.metadata.create_all(bind=engine)

    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns: list[str] = [row[1] for row in result]

            # Добавляем недостающие столбцы для статистики пользователей
            if 'tasks_created_count' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN tasks_created_count INTEGER DEFAULT 0"))

            if 'tasks_completed_count' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN tasks_completed_count INTEGER DEFAULT 0"))

            if 'tasks_received_count' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN tasks_received_count INTEGER DEFAULT 0"))

            if 'tasks_deleted_count' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN tasks_deleted_count INTEGER DEFAULT 0"))

            # Добавляем новые столбцы для расширенной статистики
            if 'total_messages_count' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN total_messages_count INTEGER DEFAULT 0"))

            if 'last_active_date' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN last_active_date DATETIME DEFAULT CURRENT_TIMESTAMP"))

            if 'joined_date' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN joined_date DATETIME DEFAULT CURRENT_TIMESTAMP"))

            if 'onesignal_notifications_sent' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN onesignal_notifications_sent INTEGER DEFAULT 0"))

            if 'onesignal_notifications_received' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN onesignal_notifications_received INTEGER DEFAULT 0"))

            conn.commit()

            # Создаем начальную запись в AppStats если таблица пуста
            app_stats_count = conn.execute(text("SELECT COUNT(*) FROM app_stats")).scalar()
            if app_stats_count == 0:
                conn.execute(text(
                    "INSERT INTO app_stats (total_users, active_users, total_tasks, completed_tasks, onesignal_notifications_total) VALUES (0, 0, 0, 0, 0)"))
                conn.commit()

    except Exception as e:
        print(f"Ошибка миграции: {e}")


def get_db():
    """Создает сессию базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()