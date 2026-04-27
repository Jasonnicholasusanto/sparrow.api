from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.watchlist_item import WatchlistItemOut


class WatchlistVisibility(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"
    SHARED = "shared"


class StockAllocationType(str, Enum):
    PERCENTAGE = "percentage"
    UNIT = "unit"


class WatchlistInputBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    visibility: WatchlistVisibility = WatchlistVisibility.PRIVATE
    allocation_type: StockAllocationType
    is_default: bool = False


class WatchlistCreate(WatchlistInputBase):
    original_author_id: UUID = None


class WatchlistUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    visibility: Optional[WatchlistVisibility] = None
    allocation_type: Optional[StockAllocationType] = None
    is_default: Optional[bool] = None


class WatchlistForkMeta(BaseModel):
    forked_from_id: Optional[int] = None
    forked_at: Optional[datetime] = None
    fork_count: int = 0
    original_author_id: UUID = None


class WatchlistOut(WatchlistInputBase, WatchlistForkMeta):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    items: Optional[List[WatchlistItemOut]] = None


class WatchlistPublicOut(WatchlistInputBase, WatchlistForkMeta):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class WatchlistCountsOut(BaseModel):
    owned: int
    forked: int
    shared: int
    bookmarked: int


class UserWatchlistsGroupedResultsOut(BaseModel):
    created: List[WatchlistOut]
    forked: List[WatchlistOut]
    shared: List[WatchlistOut]
    bookmarked: List[WatchlistOut]
    total_count: int
    counts: WatchlistCountsOut


class UserWatchlistsResponseOut(BaseModel):
    limit: int
    offset: int
    results: UserWatchlistsGroupedResultsOut


class WatchlistForkOut(BaseModel):
    message: str
    forked_watchlist: WatchlistOut
    forked_items: Optional[List[WatchlistItemOut]] = None


class WatchlistForkListOut(BaseModel):
    message: str
    count: int
    forks: List[WatchlistPublicOut]


class WatchlistLineageOut(BaseModel):
    original_author_id: UUID
    forked_from_id: Optional[int]
    forked_at: Optional[datetime]
    fork_count: int