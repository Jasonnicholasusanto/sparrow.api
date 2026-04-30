from datetime import datetime
from typing import Optional
from sqlalchemy.dialects import postgresql
from sqlmodel import Column, Field, SQLModel, text


class Tags(SQLModel, table=True):
    __tablename__ = "tags"
    __table_args__ = {"schema": "public"}

    id: int = SQLModel.Field(default=None, primary_key=True)
    name: str = SQLModel.Field(index=True)
    slug: Optional[str] = None
    category: Optional[str] = None
    is_system: bool = SQLModel.Field(default=False)
    created_at: datetime = Field(
        sa_column=Column(
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("timezone('utc'::text, now())"),
        )
    )