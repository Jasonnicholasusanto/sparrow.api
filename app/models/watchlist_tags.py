from datetime import datetime
from sqlalchemy.dialects import postgresql
from sqlmodel import Column, Field, SQLModel, text


class WatchlistTags(SQLModel, table=True):
    __tablename__ = "watchlist_tags"
    __table_args__ = {"schema": "public"}

    id: int = SQLModel.Field(default=None, primary_key=True)
    watchlist_id: int = SQLModel.Field(foreign_key="public.watchlists.id", index=True)
    tag_id: int = SQLModel.Field(foreign_key="public.tags.id", index=True)
    created_at: datetime = Field(
        sa_column=Column(
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("timezone('utc'::text, now())"),
        )
    )
    
    