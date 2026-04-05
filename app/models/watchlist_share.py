from datetime import datetime
import uuid
from sqlmodel import Field, SQLModel
from sqlalchemy import Column, text
from sqlalchemy.dialects import postgresql


class WatchlistShare(SQLModel, table=True):
    """
    ORM mapping for public.watchlist_share.
    """

    __tablename__ = "watchlist_share"
    __table_args__ = {"schema": "public"}

    watchlist_id: int = Field(foreign_key="public.watchlist.id", primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="public.user_profile.id", primary_key=True)
    can_edit: bool = Field(nullable=False, default=False)
    created_at: datetime = Field(
        sa_column=Column(
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("timezone('utc'::text, now())"),
        )
    )
