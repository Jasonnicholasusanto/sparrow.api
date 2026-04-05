from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Column, Index, text
from sqlalchemy.dialects import postgresql
from sqlmodel import SQLModel, Field


class WatchlistItem(SQLModel, table=True):
    """
    ORM mapping for public.watchlist_item.
    """

    __tablename__ = "watchlist_item"
    __table_args__ = (
        # Mirrors chk_position_nonneg
        CheckConstraint(
            '(("position" IS NULL) OR ("position" >= 0))',
            name="chk_position_nonneg",
        ),
        # Handy composite index for ordered lists (optional, matches common queries)
        Index("ix_watchlist_item_watchlist_position", "watchlist_id", "position"),
        {"schema": "public"},
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    watchlist_id: int = Field(foreign_key="public.watchlist.id", index=True)

    symbol: str = Field(index=True)
    exchange: str = Field(index=True)
    note: Optional[str] = None
    position: Optional[int] = None
    quantity: Optional[float] = None
    purchase_price: Optional[float] = None

    created_at: datetime = Field(
        sa_column=Column(
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("timezone('utc'::text, now())"),
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("timezone('utc'::text, now())"),
        )
    )
