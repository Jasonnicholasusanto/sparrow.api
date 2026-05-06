from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import text
from sqlmodel import Column, Field, SQLModel
from sqlalchemy.dialects import postgresql


class FavouriteStock(SQLModel, table=True):
    __tablename__ = "favourite_stock"
    __table_args__ = {"schema": "public"}

    id: int = Field(default=None, nullable=False, primary_key=True)
    user_id: UUID = Field(foreign_key="public.user_profile.id", index=True)
    symbol: str = Field(index=True, nullable=False)
    exchange: str = Field(index=True, nullable=False)
    note: Optional[str] = Field(default=None, nullable=True)
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
