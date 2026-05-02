from datetime import datetime
from typing import Optional
from sqlalchemy.dialects import postgresql
from sqlmodel import Column, Field, SQLModel, text


class Tags(SQLModel, table=True):
    __tablename__ = "tags"
    __table_args__ = {"schema": "public"}

    id: int = Field(default=None, nullable=False, primary_key=True)
    name: str = Field(index=True)
    slug: Optional[str] = None
    category: Optional[str] = None
    is_system: bool = Field(default=False)
    created_at: datetime = Field(
        sa_column=Column(
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("timezone('utc'::text, now())"),
        )
    )