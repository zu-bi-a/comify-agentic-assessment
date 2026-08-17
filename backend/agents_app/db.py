from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit

from agents.extensions.memory import SQLAlchemySession
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Column,
    ForeignKey,
    Index,
    MetaData,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

DEFAULT_DATABASE_URL = "postgresql+asyncpg://giva:giva@localhost:5433/giva"


def _normalize_database_url(url: str) -> str:
    """Coerce a plain postgres:// / postgresql:// URL (as issued by most
    hosting providers, e.g. Render) to the asyncpg driver SQLAlchemy needs."""
    parts = urlsplit(url)
    if parts.scheme in ("postgres", "postgresql"):
        parts = parts._replace(scheme="postgresql+asyncpg")
        url = urlunsplit(parts)
    return url


DATABASE_URL = _normalize_database_url(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))

engine: AsyncEngine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

metadata = MetaData()

threads = Table(
    "threads",
    metadata,
    Column("id", String, primary_key=True),
    Column("title", String, nullable=False, server_default="New chat"),
    Column("agent_name", String, nullable=False, server_default="Triage Agent"),
    Column("created_at", TIMESTAMP(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", TIMESTAMP(timezone=True), server_default=func.now(), nullable=False),
)

chat_messages = Table(
    "chat_messages",
    metadata,
    Column("id", String, primary_key=True),
    Column(
        "thread_id",
        String,
        ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("role", String, nullable=False),
    Column("text", Text, nullable=False),
    Column("quick_replies", JSON, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True), server_default=func.now(), nullable=False),
    Index("idx_chat_messages_thread_created", "thread_id", "created_at"),
)

templates = Table(
    "templates",
    metadata,
    Column("id", String, primary_key=True),
    Column("channel", String, nullable=False),
    Column("name", String, nullable=False),
    Column("brand", String, nullable=False),
    Column("payload", JSON, nullable=False),
    Column("status", String, nullable=False, server_default="saved"),
    Column("created_at", TIMESTAMP(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=True),
)


def agent_session(thread_id: str) -> SQLAlchemySession:
    """The Agents SDK's own turn-by-turn history (tool calls, model items, ...)
    for one thread, backed by the same Postgres database."""
    return SQLAlchemySession(session_id=thread_id, engine=engine, create_tables=False)


async def init_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    # Bootstraps the Agents SDK's agent_sessions/agent_messages tables once,
    # via its public API rather than the create_tables=True per-request path.
    bootstrap = SQLAlchemySession(session_id="__bootstrap__", engine=engine, create_tables=True)
    await bootstrap.get_items()
