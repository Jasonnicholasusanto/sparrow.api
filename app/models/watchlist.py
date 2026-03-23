from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, UniqueConstraint, text
from sqlalchemy.dialects import postgresql
from sqlmodel import SQLModel, Field

from app.schemas.watchlist import StockAllocationType, WatchlistVisibility


class Watchlist(SQLModel, table=True):
    """
    ORM mapping for public.watchlist.
    Mirrors your SQL DDL; does not attempt to create the enum type.
    """

    __tablename__ = "watchlist"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="ux_watchlist_user_name"),
        {"schema": "public"},
    )

    id: int = Field(default=None, primary_key=True)

    user_id: UUID = Field(foreign_key="public.user_profile.id", index=True)

    name: str = Field(index=False)
    description: Optional[str] = None

    is_default: bool = Field(default=False)

    # Use existing Postgres enum type "public.watchlist_visibility"
    visibility: WatchlistVisibility = Field(
        sa_column=Column(
            "visibility",
            postgresql.ENUM(
                WatchlistVisibility,
                name="watchlist_visibility",
                schema="public",
                create_type=False,
                values_callable=lambda e: [i.value for i in e],
                validate_strings=True,
            ),
            nullable=False,
            server_default=text("'private'::watchlist_visibility"),
        )
    )

    allocation_type: Optional[StockAllocationType] = Field(
        sa_column=Column(
            "allocation_type",
            postgresql.ENUM(
                StockAllocationType,
                name="stock_allocation_type",
                schema="public",
                create_type=False,
                values_callable=lambda e: [i.value for i in e],
                validate_strings=True,
            ),
            nullable=False,
        )
    )

    forked_from_id: int = Field(foreign_key="public.watchlist.id", index=True)
    forked_at: Optional[datetime] = None
    fork_count: Optional[int] = 0
    original_author_id: UUID = Field(foreign_key="public.user_profile.id", index=True)

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
