from datetime import datetime
from enum import Enum
from typing import Optional
import uuid
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from sqlmodel import Column, Field, SQLModel


class WatchlistAuditAction(str, Enum):
    WATCHLIST_CREATED = "WATCHLIST_CREATED"
    WATCHLIST_UPDATED = "WATCHLIST_UPDATED"
    WATCHLIST_DELETED = "WATCHLIST_DELETED"
    ITEM_ADDED = "ITEM_ADDED"
    ITEM_BULK_ADDED = "ITEM_BULK_ADDED"
    ITEM_UPDATED = "ITEM_UPDATED"
    ITEM_DELETED = "ITEM_DELETED"
    WATCHLIST_SHARED = "WATCHLIST_SHARED"
    SHARE_UPDATED = "SHARE_UPDATED"
    WATCHLIST_BOOKMARKED = "WATCHLIST_BOOKMARKED"
    WATCHLIST_UNBOOKMARKED = "WATCHLIST_UNBOOKMARKED"
    WATCHLIST_FORKED = "WATCHLIST_FORKED"
    WATCHLIST_PULLED = "WATCHLIST_PULLED"


class WatchlistAuditEvent(SQLModel, table=True):
    __tablename__ = "watchlist_audit_events"

    id: int = Field(default=None, primary_key=True)

    watchlist_id: Optional[int] = Field(default=None, index=True)

    user_profile_id: uuid.UUID = Field(foreign_key="public.user_profile.id", index=True)

    action: WatchlistAuditAction = Field(
        sa_column=Column(
            "action",
            postgresql.ENUM(
                WatchlistAuditAction,
                name="watchlist_audit_action",
                schema="public",
                create_type=False,
                values_callable=lambda e: [i.value for i in e],
                validate_strings=True,
            ),
            nullable=False,
        )
    )

    item_id: Optional[int] = Field(default=None, index=True)

    before_data: Optional[dict] = Field(
        default=None,
        sa_column=Column(postgresql.JSONB, nullable=True),
    )
    after_data: Optional[dict] = Field(
        default=None,
        sa_column=Column(postgresql.JSONB, nullable=True),
    )
    meta_data: Optional[dict] = Field(
        default=None,
        sa_column=Column(postgresql.JSONB, nullable=True),
    )

    created_at: datetime = Field(
        sa_column=Column(
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("timezone('utc'::text, now())"),
        )
    )
