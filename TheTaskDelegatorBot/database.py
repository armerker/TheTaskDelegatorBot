from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

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

    tasks_created_count = Column(Integer, default=0)
    tasks_completed_count = Column(Integer, default=0)
    tasks_received_count = Column(Integer, default=0)
    tasks_deleted_count = Column(Integer, default=0)

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


def init_db():
    Base.metadata.create_all(bind=engine)

    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result]

            if 'tasks_created_count' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN tasks_created_count INTEGER DEFAULT 0"))

            if 'tasks_completed_count' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN tasks_completed_count INTEGER DEFAULT 0"))

            if 'tasks_received_count' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN tasks_received_count INTEGER DEFAULT 0"))

            if 'tasks_deleted_count' not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN tasks_deleted_count INTEGER DEFAULT 0"))

            conn.commit()
    except Exception as e:
        print(f"Ошибка миграции: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()