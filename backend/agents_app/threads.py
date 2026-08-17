from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, insert, select, update

from .db import async_session, chat_messages, threads

DEFAULT_TITLE = "New chat"
_TITLE_MAX_LEN = 60


def derive_title(message: str) -> str:
    """A short thread title auto-derived from a user's first message."""
    text = " ".join(message.split())
    if not text:
        return DEFAULT_TITLE
    if len(text) <= _TITLE_MAX_LEN:
        return text
    return text[:_TITLE_MAX_LEN].rstrip() + "…"


async def create_thread() -> dict:
    thread_id = str(uuid.uuid4())
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                insert(threads).values(id=thread_id, title=DEFAULT_TITLE).returning(threads)
            )
            return dict(result.one()._mapping)


async def list_threads() -> list[dict]:
    async with async_session() as session:
        result = await session.execute(select(threads).order_by(threads.c.updated_at.desc()))
        return [dict(row._mapping) for row in result.all()]


async def get_thread(thread_id: str) -> dict | None:
    async with async_session() as session:
        result = await session.execute(select(threads).where(threads.c.id == thread_id))
        row = result.one_or_none()
        return dict(row._mapping) if row else None


async def rename_thread(thread_id: str, title: str) -> dict | None:
    title = title.strip() or DEFAULT_TITLE
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                update(threads)
                .where(threads.c.id == thread_id)
                .values(title=title, updated_at=datetime.now(timezone.utc))
                .returning(threads)
            )
            row = result.one_or_none()
            return dict(row._mapping) if row else None


async def delete_thread(thread_id: str) -> bool:
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(delete(threads).where(threads.c.id == thread_id))
            return result.rowcount > 0


async def touch_thread(thread_id: str, *, agent_name: str, title: str | None = None) -> None:
    """Update the agent currently active on this thread and bump updated_at.
    Pass `title` only when the thread should be (re)titled, e.g. right after
    its first message -- otherwise the existing title is left alone."""
    values: dict = {"agent_name": agent_name, "updated_at": datetime.now(timezone.utc)}
    if title is not None:
        values["title"] = title
    async with async_session() as session:
        async with session.begin():
            await session.execute(update(threads).where(threads.c.id == thread_id).values(**values))


async def add_message(
    thread_id: str, role: str, text: str, quick_replies: list[str] | None = None
) -> dict:
    message_id = str(uuid.uuid4())
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                insert(chat_messages)
                .values(
                    id=message_id,
                    thread_id=thread_id,
                    role=role,
                    text=text,
                    quick_replies=quick_replies,
                )
                .returning(chat_messages)
            )
            return dict(result.one()._mapping)


async def list_messages(thread_id: str) -> list[dict]:
    async with async_session() as session:
        result = await session.execute(
            select(chat_messages)
            .where(chat_messages.c.thread_id == thread_id)
            .order_by(chat_messages.c.created_at.asc())
        )
        return [dict(row._mapping) for row in result.all()]
