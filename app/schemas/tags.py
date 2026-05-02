from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TagBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    slug: Optional[str] = Field(default=None, max_length=60)
    category: Optional[str] = Field(default=None, max_length=50)
    is_system: bool = False

class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    slug: Optional[str] = Field(default=None, max_length=60)
    category: Optional[str] = Field(default=None, max_length=50)
    is_system: Optional[bool] = None

class TagOut(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

class TagSearchOut(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    public_watchlist_count: int = 0