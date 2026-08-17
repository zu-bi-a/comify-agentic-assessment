from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import insert, select, update

from .db import async_session, templates


async def add_template(channel: str, name: str, brand_name: str, payload: dict) -> dict:
    record_id = str(uuid.uuid4())
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                insert(templates)
                .values(
                    id=record_id,
                    channel=channel,
                    name=name,
                    brand=brand_name,
                    payload=payload,
                    status="saved",
                )
                .returning(templates)
            )
            return dict(result.one()._mapping)


async def list_templates(channel: str | None = None) -> list[dict]:
    async with async_session() as session:
        stmt = select(templates).order_by(templates.c.created_at.asc())
        if channel:
            stmt = stmt.where(templates.c.channel == channel)
        result = await session.execute(stmt)
        return [dict(row._mapping) for row in result.all()]


async def get_template(template_id: str) -> dict | None:
    async with async_session() as session:
        result = await session.execute(select(templates).where(templates.c.id == template_id))
        row = result.one_or_none()
        return dict(row._mapping) if row else None


async def update_template(template_id: str, name: str, payload: dict) -> dict | None:
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                update(templates)
                .where(templates.c.id == template_id)
                .values(name=name, payload=payload, updated_at=datetime.now(timezone.utc))
                .returning(templates)
            )
            row = result.one_or_none()
            return dict(row._mapping) if row else None
