import os
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


def _normalize_database_url(raw_url: Optional[str]) -> Optional[str]:
    if not raw_url:
        return None
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
    return raw_url


DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL"))
engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None
Base = declarative_base()


class StreamSession(Base):
    __tablename__ = "stream_sessions"

    id = Column(Integer, primary_key=True, index=True)
    live_chat_id = Column(String(128), unique=True, index=True, nullable=False)
    origin = Column(String(32), nullable=True)
    channel_url = Column(Text, nullable=True)
    video_id = Column(String(128), nullable=True)
    video_url = Column(Text, nullable=True)
    next_page_token = Column(Text, nullable=True)
    total_comments = Column(Integer, nullable=False, default=0)

    messages = relationship("StreamMessage", back_populates="session", cascade="all, delete-orphan")


class StreamMessage(Base):
    __tablename__ = "stream_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("stream_sessions.id"), nullable=False, index=True)
    message_id = Column(String(128), unique=True, index=True, nullable=True)
    username = Column(String(255), nullable=False)
    comment_text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    session = relationship("StreamSession", back_populates="messages")


def init_db() -> None:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required but not set.")
    print("TEMP: Initializing database schema")
    if engine:
        Base.metadata.create_all(bind=engine)
        print("TEMP: Database schema ready")
        # Best-effort migrations for dev/prod without Alembic
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE stream_sessions ADD COLUMN IF NOT EXISTS origin VARCHAR(32);"))
                conn.execute(text("ALTER TABLE stream_sessions ADD COLUMN IF NOT EXISTS channel_url TEXT;"))
                conn.execute(text("ALTER TABLE stream_sessions ADD COLUMN IF NOT EXISTS video_id VARCHAR(128);"))
                conn.execute(text("ALTER TABLE stream_sessions ADD COLUMN IF NOT EXISTS video_url TEXT;"))
                conn.execute(text("ALTER TABLE stream_messages ADD COLUMN IF NOT EXISTS message_id VARCHAR(128);"))
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_stream_messages_message_id ON stream_messages (message_id);"))
        except Exception as e:
            print("TEMP: DB migration skipped/failed:", str(e))


def get_db_session():
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is required but not set.")
    return SessionLocal()


def get_or_create_stream_session(
    db,
    live_chat_id: str,
    reset_on_new_live_chat: bool = True,
    video_id: Optional[str] = None,
    video_url: Optional[str] = None,
    origin: Optional[str] = None,
    channel_url: Optional[str] = None
) -> StreamSession:
    session = db.query(StreamSession).filter(StreamSession.live_chat_id == live_chat_id).first()
    if session:
        return session
    if reset_on_new_live_chat:
        clear_stream_data(db)
    session = StreamSession(
        live_chat_id=live_chat_id,
        origin=origin,
        channel_url=channel_url,
        video_id=video_id,
        video_url=video_url
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_current_stream_session(db) -> Optional[StreamSession]:
    return db.query(StreamSession).order_by(StreamSession.id.desc()).first()


def clear_stream_data(db) -> None:
    # Fast reset (avoids long deletes/locks when many rows)
    db.execute(text("TRUNCATE TABLE stream_messages, stream_sessions RESTART IDENTITY CASCADE;"))
    db.commit()


def update_stream_session(
    db,
    session: StreamSession,
    next_page_token: Optional[str] = None,
    total_comments: Optional[int] = None,
    video_id: Optional[str] = None,
    video_url: Optional[str] = None
) -> None:
    if next_page_token is not None:
        session.next_page_token = next_page_token
    if total_comments is not None:
        session.total_comments = total_comments
    if video_id is not None:
        session.video_id = video_id
    if video_url is not None:
        session.video_url = video_url
    db.commit()


def add_messages(db, session: StreamSession, messages: List[Dict]) -> None:
    if not messages:
        return
    rows = []
    for message in messages:
        rows.append({
            "session_id": session.id,
            "message_id": message.get("message_id"),
            "username": message.get("username", "Unknown"),
            "comment_text": message.get("comment_text", ""),
        })
    stmt = pg_insert(StreamMessage.__table__).values(rows).on_conflict_do_nothing(index_elements=["message_id"])
    db.execute(stmt)
    db.commit()
